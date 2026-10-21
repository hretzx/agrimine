"""
tests/test_release.py
---------------------
The release zip (tools/make_release.py) must hold everything needed to run with Python only, and nothing that must not ship.
Needs the built site (make build) and git; skipped otherwise.
"""
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(not (ROOT / "web" / "out" / "index.html").exists(), reason="run `make build` first")


@pytest.fixture(scope="module")
def names(tmp_path_factory):
    out = tmp_path_factory.mktemp("release") / "r.zip"
    subprocess.run([sys.executable, str(ROOT / "tools" / "make_release.py"), "--out", str(out)], check=True, capture_output=True)
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        return {n.split("/", 1)[1] for n in z.namelist() if "/" in n and not n.endswith("/")}


def test_the_release_runs_with_python_only(names):
    for needed in ("web/out/index.html", "web/out/en/index.html", "web/out/mr/index.html", "web/out/en/teachers/hierarchical/index.html",
                   "data/Crop_recommendation.csv", "requirements.txt", "README.md", "api/main.py", "api/openapi.json", "core/teachers.py",
                   "teachers-lab/app.py", "teachers-lab/pages/17_For_Teachers.py"):
        assert needed in names, needed
    assert any(n.startswith("web/out/_next/") for n in names)                      # the built scripts and styles


def test_the_release_leaves_out_what_must_not_ship(names):
    for n in names:
        assert not n.startswith(("web/node_modules/", "web/.next/", "shots/", "web/e2e/__screenshots__/", "dist/")), n
        assert "__pycache__" not in n and not n.endswith((".pyc", ".db")) and ".bak" not in n, n
    assert "teachers-lab/pages/14_What_Should_I_Grow.py" not in names              # the old farmer pages are gone from the lab
    assert "data/agrimine.db" not in names                                          # nobody's saved checks travel with the zip

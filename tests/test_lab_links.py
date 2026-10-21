"""
tests/test_lab_links.py
-----------------------
The web app's "Open in the lab" links (web/lib/lab.ts) must point at pages the lab really has. The lab's page addresses come
from its file names (teachers-lab/utils/style.page_slug), so this reads both and compares. Needs Streamlit (the lab's own code).
Run: pytest tests/test_lab_links.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / "teachers-lab"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(LAB))

from utils.style import page_slug  # noqa: E402  (the lab's own utils package)

SOURCE = (ROOT / "web" / "lib" / "lab.ts").read_text()


def _linked() -> dict[str, str]:
    block = SOURCE.split("export const LAB_PAGE = {")[1].split("} as const")[0]
    return dict(re.findall(r'(\w+):\s*"([a-z0-9-]+)"', block))


def test_every_web_link_names_a_real_lab_page():
    lab_pages = {page_slug(p.stem) for p in (LAB / "pages").glob("*.py")}
    linked = _linked()
    assert len(linked) >= 7
    missing = {k: v for k, v in linked.items() if v not in lab_pages}
    assert not missing, f"links to lab pages that do not exist: {missing}"


def test_the_algorithms_on_the_teachers_page_and_the_links_agree():
    page = (ROOT / "web" / "app" / "[lang]" / "teachers" / "page.tsx").read_text()
    algos = set(re.findall(r'"(\w+)"', re.search(r"const ALGOS = \[(.*?)\] as const", page, re.S).group(1)))
    assert set(_linked()) <= algos, "a link for an algorithm the teachers page does not list"

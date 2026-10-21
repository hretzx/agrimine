"""
tools/make_release.py
---------------------
Pack the release zip: every file git tracks (the committed state, so nothing half-edited slips in) plus the PREBUILT web app
(web/out), so whoever receives it needs Python only, never Node.

    python tools/make_release.py                 # -> dist/agrimine-release.zip
    python tools/make_release.py --out some.zip

Run `make build` first (it creates web/out). Left out on purpose: browser-test screenshots, loose screenshots, measuring
reports, anything git does not track (databases, caches, node_modules).
"""
import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOP = "agrimine"                                   # the folder the zip unpacks into
SKIP_PREFIXES = ("web/e2e/__screenshots__/", "shots/", "web/test-results/")
SKIP_NAMES = {"measure_compare_report.txt", "measure_rect_report.txt", ".shot-server.log"}
REQUIRED = ("web/out/index.html", "data/Crop_recommendation.csv", "requirements.txt", "api/main.py", "core/advice.py", "teachers-lab/app.py", "README.md")


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout.decode()
    return [f for f in out.split("\0") if f]


def release_files() -> list[str]:
    files = [f for f in tracked_files() if not f.startswith(SKIP_PREFIXES) and Path(f).name not in SKIP_NAMES and (ROOT / f).is_file()]
    built = ROOT / "web" / "out"
    if not (built / "index.html").exists():
        sys.exit("web/out is missing: run `make build` first (the release ships the prebuilt site).")
    files += sorted(str(p.relative_to(ROOT)) for p in built.rglob("*") if p.is_file())
    return sorted(set(files))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "dist" / "agrimine-release.zip"))
    out = Path(ap.parse_args().out)
    out.parent.mkdir(parents=True, exist_ok=True)
    files = release_files()
    missing = [r for r in REQUIRED if r not in files]
    if missing:
        sys.exit(f"the release would be missing: {missing}")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(ROOT / f, f"{TOP}/{f}")
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB, {len(files)} files)")


if __name__ == "__main__":
    main()

"""
tests/test_web_glyphs.py
------------------------
Every crop in core/crops.py has a hand-drawn glyph and a tint in the web app (web/components/farm/glyph-data.ts), and the
file holds nothing for a crop that no longer exists. A crop without a drawing would show a neutral leaf on the farmer's screen.
Run: pytest tests/test_web_glyphs.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.crops import CROPS_BY_KEY  # noqa: E402

DATA = (ROOT / "web" / "components" / "farm" / "glyph-data.ts").read_text()


def _keys(block: str) -> set[str]:
    return set(re.findall(r'^  "([a-z]+)":', block, re.M))


def test_every_crop_has_a_drawing_and_a_tint():
    glyphs, tints = DATA.split("export const GLYPH_TINT")
    assert _keys(glyphs) == set(CROPS_BY_KEY), "crops without a drawing / drawings without a crop: " + str(_keys(glyphs) ^ set(CROPS_BY_KEY))
    assert _keys(tints) == set(CROPS_BY_KEY)


def test_each_drawing_is_a_32_unit_svg_body_with_at_least_two_colours():
    glyphs = DATA.split("export const GLYPH_TINT")[0]
    for key, body in re.findall(r'^  "([a-z]+)": "((?:[^"\\]|\\.)*)",$', glyphs, re.M):
        colours = set(re.findall(r'#[0-9A-Fa-f]{6}', body))
        assert len(colours) >= 2, f"{key}: a drawing needs at least two colours"
        assert "<script" not in body and "onload" not in body.lower()
        shapes = re.sub(r'rotate\(-?[\d.]+', 'rotate(', re.sub(r'#[0-9A-Fa-f]{6}|opacity="[\d.]+"', '', body))      # a rotation angle is not a coordinate
        nums = [float(n) for n in re.findall(r'(?<![#\w])-?\d+(?:\.\d+)?', shapes)]
        assert max(nums) <= 40 and min(nums) >= -5, f"{key}: coordinates outside the 32x32 box"

"""
utils/farm_ui.py
----------------
Look and feel of the farmer-facing pages ("Sage Field": sage sidebar, ivory page, white cards, near-black navy
text, pastel summary cards, green / yellow / coral status colours). utils/style.py holds the shared tokens and
base CSS; this file adds what Home, What should I grow?, Crop Doctor, Plan B and For teachers need:

  1. FARM_CSS        - the extra stylesheet. Every size is written as U(n): n "design pixels" of the reference
                       layout (1536 x 1024), scaled to the window by --u, so the Home page keeps its proportions
                       and fits one screen at 1366 x 768, 1440 x 900, 1536 x 1024 and larger.
  2. Sidebar nav     - one link, to the landing page (register_pages() is called by app.py; draw_nav() draws it).
  3. top_bar()       - greeting, English / Marathi toggle and the "New Soil Check" button.
  4. HTML helpers    - summary_card, hero_card, rank_row, status_row, ring, pill ... they RETURN an HTML string
                       (all text escaped); show it with st.markdown(html, unsafe_allow_html=True).
  5. farm_card()     - a card with an icon, title and one-line subtitle around whatever its `with` block draws.
"""
import base64
import re
import urllib.parse
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import streamlit as st

from utils.i18n import CHOICE_KEY, LANGS, crop_name, get_lang, t
from utils.session import SOIL_PAGE
from utils.style import STATUS_BAD, STATUS_GOOD, STATUS_MODERATE, _esc, crop_emoji

# ---------------------------------------------------------------- 1. stylesheet
_CSS_TEMPLATE = """
<style>
:root { --u: max(0.8px, min(calc(100vw / 1536), calc(100vh / 1024))); }

/* ===== Page frame: sidebar 243, then 22 of air on the left and 18 on the right ===== */
[data-testid="stSidebar"] { width: 15.82vw !important; min-width: 15.82vw !important; max-width: 15.82vw !important; }
[data-testid="stMainBlockContainer"] { max-width: none !important; padding: U(20) U(18) U(16) U(22) !important; }
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] { gap: U(14); }
/* The injected <style> blocks sit in their own (empty) elements; keep them from adding gaps. They still apply. */
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] style), [data-testid="stElementContainer"]:has(> style) { display: none; }
.st-key-am_sumrow { height: U(103); margin-bottom: U(3); flex: 0 0 auto !important; }
.st-key-am_home { gap: U(14) !important; }
.st-key-am_home > :last-child { margin-top: U(-2); }
[data-testid="stSidebarContent"] { min-height: 100vh; }
[data-testid="stHeader"] { height: 0 !important; min-height: 0 !important; background: transparent !important; }

/* ===== Sidebar ===== */
.st-key-am_brand { order: 1; padding: U(28) 0 U(16) U(2); margin-top: U(-60); }
.brand-logo { width: U(42); height: U(42); }
.brand-name { font-size: U(25); color: #064A34; font-weight: 700; letter-spacing: -0.02em; }
.brand-tag { font-size: U(10); color: #5F8681; letter-spacing: 0.01em; text-transform: none; font-weight: 500; margin-top: U(4); }
.st-key-am_nav { order: 2; padding: 0; }
.st-key-am_nav { flex: 0 0 auto !important; gap: U(26.5) !important; margin: U(18) 0 0 U(-14); width: U(217); }
.st-key-am_nav [data-testid="stPageLink"] a { border-radius: U(12); padding: 0 U(14); height: U(42); min-height: 0; gap: U(12); }
.st-key-am_nav [data-testid="stPageLink"] a p { color: #0B212C; font-weight: 500; font-size: U(14); }
.st-key-am_nav [data-testid="stPageLink"] a span[data-testid="stIconMaterial"] { color: #0A4C31; font-size: U(24); }
.st-key-am_nav [data-testid="stPageLink"] a:hover { background: rgba(47, 143, 91, 0.10); }
.st-key-am_nav [data-testid="stPageLink"] a[aria-current="page"] { background: #C9E4C7; }
.st-key-am_nav [data-testid="stPageLink"] a[aria-current="page"] p { font-weight: 700; color: #032D15; }
/* the tagline sits just above the landscape (282 design px tall), like the reference */
.st-key-am_tagline { position: fixed; left: U(22); bottom: U(300); width: U(170); z-index: 2; }
/* The landscape is the sidebar's own background, anchored to its bottom edge and as wide as the sidebar */
[data-testid="stSidebar"] { background-image: url("__HILLS__"); background-repeat: no-repeat; background-position: left bottom; background-size: 100% auto; }
[data-testid="stSidebarContent"] { background: transparent; }
.am-tagline { font-style: italic; color: #425E69; font-size: U(15); line-height: 1.55; font-family: Georgia, 'Times New Roman', serif; }
.st-key-am_side_assess { order: 3; margin-top: U(30) !important; padding-top: U(10); }

/* ===== Header: greeting, language toggle, button ===== */
.st-key-am_topbar { height: U(54); flex: 0 0 auto !important; overflow: visible; }
.greet-title { font-size: U(24); font-weight: 700; color: var(--am-ink); letter-spacing: -0.015em; line-height: 1.2; }
.greet-sub { color: #324B58; font-size: U(13); margin-top: U(4); }
[data-testid="stSegmentedControl"] { background: #FFFFFF; border: 1px solid var(--am-line); border-radius: U(12); padding: U(3); width: fit-content; margin-left: auto; }
[data-testid="stSegmentedControl"] button { border-radius: U(9); padding: U(4) U(14); font-weight: 600; font-size: U(13); }
[data-testid="stSegmentedControl"] [data-testid="stBaseButton-segmented_controlActive"] { background: #1F7A3A !important; color: #FFFFFF !important; }
[data-testid="stSegmentedControl"] [data-testid="stBaseButton-segmented_controlActive"] * { color: #FFFFFF !important; }

/* ===== Summary cards ===== */
.st-key-am_sumrow [data-testid="stHorizontalBlock"] { gap: U(21); }
.sum-card { display: flex; align-items: center; gap: U(16); padding: 0 U(20); border-radius: U(18); height: U(103);
            background: var(--tint); border: 1px solid rgba(6, 19, 38, 0.04); box-shadow: 0 2px 10px rgba(20, 40, 30, 0.05); }
.sum-icon { flex: 0 0 U(66); width: U(66); height: U(66); border-radius: 50%; display: grid; place-items: center;
            background: var(--ico); font-size: U(30); }
.sum-label { font-size: U(13); font-weight: 600; color: var(--am-ink); }
.sum-value { font-size: U(32); font-weight: 700; line-height: 1.1; color: var(--am-ink); font-variant-numeric: tabular-nums; }
.sum-note { font-size: U(11); color: #627475; }

/* ===== Rows and cards ===== */
.st-key-am_home [data-testid="stHorizontalBlock"] { gap: U(12); }
[class*="st-key-am_farm_"], .st-key-am_hero { position: relative; border-radius: U(16); overflow: hidden; box-sizing: border-box; flex: 0 0 auto !important; }
[class*="st-key-am_farm_"] { background: #FFFFFF; border: 1px solid #EEF1EE; box-shadow: 0 2px 10px rgba(20, 40, 30, 0.06);
                             padding: U(14) U(18) U(10) U(18); }
.st-key-am_farm_top3, .st-key-am_farm_doctor, .st-key-am_hero { height: U(316); }
.st-key-am_farm_planb, .st-key-am_farm_farms, .st-key-am_farm_needs { height: U(279); }
.st-key-am_farm_req, .st-key-am_farm_gain, .st-key-am_farm_pat { height: U(180); }
[data-testid="stHorizontalBlock"]:has([class*="st-key-am_farm_"]), [data-testid="stHorizontalBlock"]:has(.st-key-am_hero) { align-items: flex-start; }
[class*="st-key-am_farm_"] > [data-testid="stVerticalBlock"] { gap: U(8); }
[class*="st-key-am_farm_"] [class*="st-key-am_chart"] { background: transparent; border: 0; box-shadow: none; padding: 0; }
.fc-head { display: flex; align-items: center; gap: U(12); }
.fc-ico { flex: 0 0 U(38); width: U(38); height: U(38); border-radius: 50%; display: grid; place-items: center; font-size: U(19); background: var(--ico); }
.fc-title { font-weight: 700; font-size: U(16); color: var(--am-ink); line-height: 1.2; }
.fc-sub { color: #556D84; font-size: U(11.5); line-height: 1.3; margin-top: U(2); }

/* Pills */
.pill { display: inline-block; font-size: U(11); font-weight: 700; padding: U(4) U(12); border-radius: 999px; white-space: nowrap; }
.pill-good { background: #D9F5E3; color: #148244; }
.pill-moderate { background: #FFF3D5; color: #B86E00; }
.pill-low, .pill-attention { background: #FFE1DD; color: #D93A48; }
.pill-fair { background: #E1EFFD; color: #2A6FB8; }
.pill-best { background: #D9F5E3; color: #148244; }

/* ===== Hero ===== */
.st-key-am_hero { background: #1D3A25; box-shadow: 0 6px 20px rgba(14, 40, 24, 0.25); border: 0; }
.st-key-am_hero > [data-testid="stVerticalBlock"] { gap: 0; }
.hero { position: relative; color: #FFFFFF; height: U(316); background-image: url("__HERO__"); background-size: 100% 100%; }
.hero-top { position: absolute; left: U(12); right: U(14); top: U(14); display: flex; justify-content: space-between; align-items: flex-start; }
.hero-title { font-size: U(22); font-weight: 700; padding-left: U(10); line-height: 1.2; text-shadow: 0 1px 6px rgba(0,0,0,.35); }
.hero-sub { font-size: U(12.5); font-weight: 500; margin-top: U(7); padding-left: U(10); color: rgba(255,255,255,.92); text-shadow: 0 1px 4px rgba(0,0,0,.4); }
.hero-badge { background: #FDF1D1; color: #B36B12; font-weight: 700; font-size: U(13); padding: U(8) U(18); border-radius: 999px; }
.hero-crop { position: absolute; left: U(24); top: U(99); width: U(106); height: U(106); border-radius: 50%; display: grid; place-items: center; font-size: U(54);
             background: radial-gradient(circle at 35% 30%, #A9D26B, #4E8B2E); border: U(3) solid #FFFFFF; }
.hero-body { position: absolute; left: U(150); right: U(18); top: U(104); }
.hero-name { font-size: U(30); font-weight: 700; line-height: 1.1; display: flex; align-items: center; gap: U(10); flex-wrap: wrap; }
.hero-pill { font-size: U(11.5); font-weight: 700; background: #0A8F55; padding: U(5) U(11); border-radius: 999px; }
.hero-why { font-size: U(12.5); line-height: 1.4; color: rgba(255,255,255,.95); margin-top: U(8); text-shadow: 0 1px 4px rgba(0,0,0,.4); }
.hero-note { font-size: U(11); color: rgba(255,255,255,.85); margin-top: U(4); text-shadow: 0 1px 4px rgba(0,0,0,.4); }
.hero-stats { position: absolute; left: 0; right: 0; bottom: 0; height: U(64); display: grid; grid-template-columns: repeat(3, 1fr);
              background: rgba(10, 30, 20, 0.55); align-items: center; }
.hero-stat { display: flex; align-items: center; gap: U(10); padding: 0 U(16); border-left: 1px solid rgba(255,255,255,.14); }
.hero-stat:first-child { border-left: 0; }
.hero-stat i { flex: 0 0 U(34); width: U(34); height: U(34); border-radius: 50%; background: rgba(255,255,255,.10); display: grid; place-items: center; font-style: normal; font-size: U(15); }
.hero-stat span { display: block; font-size: U(11); color: rgba(255,255,255,.78); }
.hero-stat b { font-size: U(15); color: #FFFFFF; font-variant-numeric: tabular-nums; }
.hero-empty { color: #FFFFFF; padding: U(22); height: U(316); background-image: url("__HERO__"); background-size: 100% 100%; }
.hero-empty p { font-size: U(14); margin-top: U(14); }
.st-key-am_hero [data-testid="stElementContainer"]:has([data-testid="stPageLink"]) { position: absolute; left: U(150); top: U(212); z-index: 3; width: auto; }
.st-key-am_hero [data-testid="stPageLink"] a { background: #049564; border-radius: 999px; padding: U(8) U(24); width: fit-content; min-height: 0; gap: U(14); box-shadow: 0 4px 14px rgba(0,0,0,.25); }
.st-key-am_hero [data-testid="stPageLink"] a:hover { background: #06A872; }
.st-key-am_hero [data-testid="stPageLink"] a p, .st-key-am_hero [data-testid="stPageLink"] a span { color: #FFFFFF !important; font-weight: 700; font-size: U(13.5); }

/* ===== Crop rows (Top 3) ===== */
.rank { display: flex; align-items: center; gap: U(14); height: U(77); padding: 0 U(12) 0 U(12); border: 1px solid #E9EFE8; border-radius: U(14);
        background: #FBFDF9; box-sizing: border-box; }
.rank-ico { flex: 0 0 U(56); width: U(56); height: U(56); border-radius: 50%; display: grid; place-items: center; font-size: U(28);
            background: radial-gradient(circle at 35% 30%, #E4F0D2, #B5D49A); border: U(2) solid #FFFFFF; box-shadow: 0 1px 4px rgba(6,19,38,.15); }
.rank-main { flex: 1 1 auto; min-width: 0; }
.rank-top { display: flex; align-items: center; justify-content: space-between; }
.rank-name { font-weight: 700; color: var(--am-ink); font-size: U(14); }
.rank-score { font-size: U(12); font-weight: 700; color: var(--am-ink); display: flex; align-items: center; gap: U(6); font-variant-numeric: tabular-nums; }
.rank-score em { font-style: normal; font-weight: 600; color: var(--am-ink-2); margin-left: U(6); font-size: U(11); }
.rank-score i { width: U(9); height: U(9); border-radius: 50%; display: inline-block; }
.rank-bar { height: U(9); background: #EBF3F3; border-radius: 99px; margin-top: U(10); overflow: hidden; }
.rank-bar i { display: block; height: 100%; border-radius: 99px; }
.rank-sub { color: #556D84; font-size: U(11); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: U(2); }
.rank-side { flex: 0 0 auto; }
.rank-compact { height: U(60); }
.rank-compact .rank-ico { flex-basis: U(46); width: U(46); height: U(46); font-size: U(23); }
.rank-compact .rank-bar { display: none; }
.rank-compact .rank-top { justify-content: flex-start; }
.rank-compact .rank-score { display: none; }
.rank-compact .rank-sub { margin-top: U(3); }

/* Streamlit pulls markdown up by 1rem; give the row groups that room back so the last row is not clipped */
.srows { padding-bottom: 1rem; }
[class*="st-key-am_farm_"] [data-testid="stMetric"] { background: transparent; border: 0; box-shadow: none; padding: 0; }
/* ===== Crop Doctor rows ===== */
.srow { display: grid; grid-template-columns: U(96) 1fr U(78); align-items: center; gap: U(10); height: U(40); border-bottom: 1px solid #F1F4F1; }
.srow:last-of-type { border-bottom: 0; }
.srow-label b { display: block; font-size: U(11.5); color: #1E2E38; font-weight: 600; }
.srow-label span { display: block; font-size: U(9.5); color: #627475; }
.sbar { position: relative; height: U(9); border-radius: 99px; background: #E9F3F5; }
.sbar .fill { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 99px; }
.sbar .band { position: absolute; top: U(-3); bottom: U(-3); border: 1.5px solid rgba(6, 19, 38, 0.18); border-radius: U(6); background: rgba(47, 181, 115, 0.10); }
.sstat { text-align: right; font-size: U(12); font-weight: 700; white-space: nowrap; }
.s-good { color: #178A4C; } .s-moderate { color: #B86E00; } .s-attention { color: #D93A48; }
.soil-overall { display: flex; align-items: center; gap: U(10); margin-top: U(10); height: U(53); padding: 0 U(14); border-radius: U(12); background: #F1F7F1; border: 1px solid #E1EDE1; box-sizing: border-box; }
.soil-overall span { font-size: U(11.5); color: #30474F; }
.soil-dots { display: flex; gap: U(5); margin-left: U(6); }
.soil-dots i { width: U(9); height: U(9); border-radius: 50%; display: inline-block; }
.soil-overall b { margin-left: auto; font-size: U(14); }

/* ===== Plan B, farms, climate ===== */
.chips { display: flex; flex-wrap: wrap; gap: U(2) U(12); font-size: U(10); color: #556D84; margin-top: U(2); }
.chips i { display: inline-block; width: U(9); height: U(9); border-radius: 50%; margin-right: U(5); }
.chart-help { color: #556D84; font-size: U(10.5); margin-top: U(2); line-height: 1.3; }
.legend-row { display: flex; align-items: flex-start; gap: U(10); margin-bottom: U(6); }
.legend-row i { flex: 0 0 U(14); width: U(14); height: U(14); border-radius: 50%; margin-top: U(2); }
.legend-row b { display: block; font-size: U(11.5); color: var(--am-ink); font-weight: 600; }
.legend-row span { display: block; font-size: U(10.5); color: #556D84; line-height: 1.25; }
.st-key-am_farm_planb [data-testid="stHorizontalBlock"] { gap: U(4); align-items: center; }
.st-key-am_farm_planb .stButton button { background: transparent; border: 0; box-shadow: none; padding: 0; min-height: U(34); color: #061326; }
.st-key-am_farm_planb .stButton button:hover { background: #EEF6EC; }
.st-key-am_chart_home_farms { height: U(196); }
.st-key-am_chart_home_needs { height: U(168); }
.st-key-am_chart_home_gain { height: U(114); }

/* ===== Requirement rings ===== */
.rings { display: grid; grid-template-columns: repeat(4, 1fr); height: U(118); }
.ring { text-align: center; border-left: 1px solid #EEF1EE; }
.ring:first-child { border-left: 0; }
.ring-label { font-size: U(10); font-weight: 700; color: #1E2E38; }
.ring svg { width: U(66); height: U(66); display: block; margin: U(1) auto 0 auto; }
.ring-val { font-size: U(9.5); font-weight: 600; fill: #1E2E38; }
.ring-stat { font-size: U(11.5); font-weight: 700; margin-top: U(4); }

/* ===== Patterns (compact) ===== */
.pat { padding: U(7) U(11); border: 1px solid #E9EFE8; border-radius: U(12); background: #FBFDF9; margin-bottom: U(7); font-size: U(11.5); color: var(--am-ink); line-height: 1.35; }
.pat small { display: block; color: #556D84; font-size: U(10); }

/* ===== For teachers hub ===== */
.hub-card { background: #FFFFFF; border: 1px solid #EEF1EE; border-radius: U(16); padding: U(16) U(18); box-shadow: 0 2px 10px rgba(20, 40, 30, 0.06); height: 100%; }
.hub-card b { font-size: U(15); color: var(--am-ink); }
.hub-algo { display: inline-block; font-size: U(10); font-weight: 700; padding: U(2) U(9); border-radius: 999px; margin-left: U(8); color: #fff; }
.hub-card p { color: #556D84; font-size: U(12.5); margin: U(6) 0 0 0; line-height: 1.5; }
</style>
"""


def _svg_uri(svg: str) -> str:
    """An SVG as a data: URI that is safe inside CSS url("...") (everything is percent-encoded)."""
    return "data:image/svg+xml;utf8," + urllib.parse.quote(svg, safe="")


# A soft landscape for the hero card (mountains, tree line, planted rows) drawn as SVG: no image file needed.
_HERO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 510 316" preserveAspectRatio="none">'
    '<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3A4E58"/><stop offset="1" stop-color="#6C8683"/></linearGradient>'
    '<linearGradient id="fld" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5C8A2A"/><stop offset="0.55" stop-color="#2F5A18"/><stop offset="1" stop-color="#0E2410"/></linearGradient>'
    '<linearGradient id="shade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#000" stop-opacity="0.10"/><stop offset="0.6" stop-color="#000" stop-opacity="0.12"/><stop offset="1" stop-color="#000" stop-opacity="0.45"/></linearGradient></defs>'
    '<rect width="510" height="316" fill="url(#sky)"/>'
    '<polygon points="0,120 70,70 130,105 210,62 290,100 370,58 450,92 510,70 510,150 0,150" fill="#4B6567" opacity="0.95"/>'
    '<polygon points="0,138 90,112 180,132 280,108 380,130 470,112 510,125 510,160 0,160" fill="#3E5C45"/>'
    '<g fill="#25451F"><circle cx="40" cy="140" r="9"/><circle cx="76" cy="144" r="7"/><circle cx="150" cy="142" r="8"/><circle cx="230" cy="141" r="10"/>'
    '<circle cx="300" cy="143" r="8"/><circle cx="360" cy="139" r="9"/><circle cx="430" cy="142" r="8"/><circle cx="480" cy="140" r="9"/></g>'
    '<rect y="148" width="510" height="168" fill="url(#fld)"/>'
    '<g stroke="#79A93A" stroke-opacity="0.35" stroke-width="3" fill="none"><path d="M0 170 Q255 160 510 172"/><path d="M0 196 Q255 184 510 200"/><path d="M0 226 Q255 212 510 232"/><path d="M0 262 Q255 244 510 270"/></g>'
    '<rect width="510" height="316" fill="url(#shade)"/></svg>'
)
_HILLS_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 243 150" preserveAspectRatio="none">'
    '<defs><linearGradient id="g1" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#EBF4E9" stop-opacity="0"/><stop offset="1" stop-color="#C9E3BC"/></linearGradient></defs>'
    '<rect width="243" height="150" fill="url(#g1)"/>'
    '<path d="M0 105 Q60 70 120 95 T243 80 V150 H0Z" fill="#B8D9A0"/><path d="M0 125 Q70 95 140 118 T243 105 V150 H0Z" fill="#8DC070"/>'
    '<path d="M0 142 Q80 118 160 136 T243 126 V150 H0Z" fill="#5FA655"/>'
    '<g fill="#3E8A4A"><path d="M40 112 l-9 22 h18z"/><path d="M40 98 l-8 20 h16z"/><path d="M200 108 l-8 20 h16z"/><path d="M200 95 l-7 18 h14z"/></g>'
    '<rect x="104" y="108" width="26" height="16" fill="#E7C98B"/><polygon points="101,108 117,96 133,108" fill="#C5663C"/></svg>'
)

def _sidebar_art() -> str:
    """The landscape at the bottom of the sidebar: assets/sidebar_landscape.jpg (cropped from the reference design),
    or the small SVG drawing above when the file is missing."""
    path = Path(__file__).resolve().parent.parent / "assets" / "sidebar_landscape.jpg"
    if path.exists():
        return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()
    return _svg_uri(_HILLS_SVG)


FARM_CSS = re.sub(r"U\((-?\d+(?:\.\d+)?)\)", r"calc(\1 * var(--u))", _CSS_TEMPLATE
                  ).replace("__HERO__", _svg_uri(_HERO_SVG)).replace("__HILLS__", _sidebar_art())
# Markdown ends an HTML block at a blank line, so the stylesheet must not contain any.
FARM_CSS = "\n".join(line for line in FARM_CSS.splitlines() if line.strip())


# ------------------------------------------------------------------ 2. sidebar nav
PAGES: dict = {}     # key -> st.Page, filled in by app.py before the navigation runs
PRIMARY = [("nav_teachers", ":material/school:")]      # the lab has one sidebar link: the landing page that lists every technical page


def register_pages(pages: dict) -> None:
    """app.py hands over the page objects so the sidebar can link to them."""
    PAGES.clear()
    PAGES.update(pages)


def draw_nav() -> None:
    """The sidebar link to the landing page. (Pages opened on their own, e.g. in tests, have no navigation to link to.)"""
    with st.sidebar.container(key="am_nav"):
        for key, icon in PRIMARY:
            if key in PAGES:
                try:
                    st.page_link(PAGES[key], label=t(key), icon=icon)
                except Exception:
                    pass


def draw_tagline() -> None:
    with st.sidebar.container(key="am_tagline"):
        st.markdown(f'<div class="am-tagline">{_esc(t("tagline"))}</div>', unsafe_allow_html=True)


# --------------------------------------------------------------------- 3. top bar
def greeting() -> str:
    hour = datetime.now().hour
    return t("greeting_morning" if hour < 12 else "greeting_afternoon" if hour < 17 else "greeting_evening")


def top_bar(title: str, subtitle: str) -> None:
    """Title and subtitle on the left; English / Marathi toggle and the New Soil Check button on the right."""
    with st.container(key="am_topbar"):
        left, lang, action = st.columns([6.2, 1.4, 1.7])
        left.markdown(f'<div class="greet-title">{_esc(title)}</div><div class="greet-sub">{_esc(subtitle)}</div>',
                      unsafe_allow_html=True)
        labels = list(LANGS)
        current = next(label for label, code in LANGS.items() if code == get_lang())
        lang.segmented_control(t("language"), labels, default=current, key=CHOICE_KEY, label_visibility="collapsed")
        if action.button(t("new_check"), type="primary", icon=":material/add:", width="stretch"):
            st.switch_page(SOIL_PAGE)


# ----------------------------------------------------------------- 4. HTML helpers
LEVEL_COLOR = {"good": STATUS_GOOD, "moderate": STATUS_MODERATE, "low": STATUS_BAD, "attention": STATUS_BAD}


def pill(text: str, level: str) -> str:
    return f'<span class="pill pill-{level}">{_esc(text)}</span>'


def summary_card(label: str, value, note: str, tint: str, ico: str, icon: str) -> str:
    return (f'<div class="sum-card" style="--tint:{tint};--ico:{ico}"><div class="sum-icon" aria-hidden="true">{icon}</div>'
            f'<div><div class="sum-label">{_esc(label)}</div><div class="sum-value">{_esc(value)}</div>'
            f'<div class="sum-note">{_esc(note)}</div></div></div>')


def rank_row(crop: str, score: float, level: str, tag: str, sub: str = "", tag_level: str | None = None,
             compact: bool = False, prob: str = "") -> str:
    """A crop with its match score (0 to 100) as a bar, a coloured dot and a status pill. prob = model probability text, shown beside it."""
    color = LEVEL_COLOR[level]
    sub_html = f'<div class="rank-sub" title="{_esc(sub)}">{_esc(sub)}</div>' if sub else ""
    return (f'<div class="rank{" rank-compact" if compact else ""}"><div class="rank-ico" aria-hidden="true">{crop_emoji(crop)}</div>'
            f'<div class="rank-main"><div class="rank-top"><span class="rank-name">{_esc(crop_name(crop))}</span>'
            f'<span class="rank-score"><i style="background:{color}"></i>{score:.0f}{f"<em>{_esc(prob)}</em>" if prob else ""}</span></div>'
            f'<div class="rank-bar" role="progressbar" aria-valuenow="{score:.0f}" aria-valuemin="0" aria-valuemax="100">'
            f'<i style="width:{max(2.0, min(100.0, score)):.0f}%;background:{color}"></i></div>{sub_html}</div>'
            f'<div class="rank-side">{pill(tag, tag_level or level)}</div></div>')


def status_row(label: str, value_text: str, range_text: str, status: str, status_text: str,
               pos: float, band: tuple[float, float]) -> str:
    """
    One soil measurement. The track is the whole range seen in the dataset; the coloured fill ends at
    your value (pos, 0 to 1) and the outlined box marks the range this crop usually grows in (band, 0 to 1).
    """
    color = LEVEL_COLOR[status]
    lo, hi = max(0.0, band[0]), min(1.0, band[1])
    return (f'<div class="srow" title="{_esc(label)}: {_esc(value_text)}, usual {_esc(range_text)}">'
            f'<div class="srow-label"><b>{_esc(label)}</b><span>{_esc(value_text)}</span></div>'
            f'<div class="sbar" role="img" aria-label="{_esc(label)}: {_esc(status_text)}">'
            f'<div class="band" style="left:{lo * 100:.1f}%;width:{max(1.0, (hi - lo) * 100):.1f}%"></div>'
            f'<div class="fill" style="width:{max(2.0, min(100.0, pos * 100)):.1f}%;background:{color}"></div></div>'
            f'<div class="sstat s-{status}">{_esc(status_text)}</div></div>')


def hero_card(title: str, sub: str, badge: str, crop: str, strong: str, why: str, note: str) -> str:
    """The top part of the hero card (the button and the stats strip are drawn separately)."""
    return (f'<div class="hero"><div class="hero-top"><div><div class="hero-title">{_esc(title)}</div>'
            f'<div class="hero-sub">{_esc(sub)}</div></div><div class="hero-badge">&#9733; {_esc(badge)}</div></div>'
            f'<div class="hero-crop" aria-hidden="true">{crop_emoji(crop)}</div>'
            f'<div class="hero-body"><div class="hero-name">{_esc(crop_name(crop))}'
            f'<span class="hero-pill">&#9733; {_esc(strong)}</span></div>'
            f'<div class="hero-why">{_esc(why)}</div><div class="hero-note">{_esc(note)}</div></div></div>')


def hero_stats(stats: list[tuple[str, str, str]]) -> str:
    """The dark strip at the bottom of the hero card: icon, label and value for pH, temperature and rainfall."""
    cells = "".join(f'<div class="hero-stat"><i aria-hidden="true">{ico}</i><div><span>{_esc(k)}</span><b>{_esc(v)}</b></div></div>'
                    for k, v, ico in stats)
    return f'<div class="hero-stats">{cells}</div>'


def ring(label: str, value_text: str, ok: bool, stat_text: str) -> str:
    """A gauge ring: a blue-to-green arc when the field sits in the crop's usual range, a coral arc when it does not."""
    gid = f"rg{abs(hash(label)) % 10**6}"
    stroke = f"url(#{gid})" if ok else STATUS_BAD
    color = "#178A4C" if ok else "#D93A48"
    return (f'<div class="ring"><div class="ring-label">{_esc(label)}</div>'
            f'<svg viewBox="0 0 66 66" role="img" aria-label="{_esc(label)}: {_esc(stat_text)}"><defs><linearGradient id="{gid}" x1="0" y1="1" x2="1" y2="0">'
            f'<stop offset="0" stop-color="#22B8E6"/><stop offset="1" stop-color="#1FD07A"/></linearGradient></defs>'
            f'<circle cx="33" cy="33" r="28" fill="none" stroke="#E7F3EE" stroke-width="5"/>'
            f'<circle cx="33" cy="33" r="28" fill="none" stroke="{stroke}" stroke-width="5" stroke-linecap="round" '
            f'stroke-dasharray="{(0.78 if ok else 0.45) * 175.9:.1f} 175.9" transform="rotate(130 33 33)"/>'
            f'<text x="33" y="37" text-anchor="middle" class="ring-val">{_esc(value_text)}</text></svg>'
            f'<div class="ring-stat" style="color:{color}">{_esc(stat_text)}</div></div>')


def safe_link(page: str, label: str, icon: str | None = None) -> None:
    """st.page_link that does nothing when the page is not registered (a page opened on its own, e.g. in tests)."""
    try:
        st.page_link(page, label=label, icon=icon)
    except Exception:
        pass


# --------------------------------------------------------------------- 5. farm_card
@contextmanager
def farm_card(key: str, title: str, subtitle: str, icon: str, tint: str = "#DDF1E2"):
    """A white card: round icon, title, one-line subtitle, then whatever the `with` block draws."""
    with st.container(key=f"am_farm_{key}"):
        st.markdown(f'<div class="fc-head"><div class="fc-ico" style="--ico:{tint}" aria-hidden="true">{icon}</div><div>'
                    f'<div class="fc-title">{_esc(title)}</div><div class="fc-sub">{_esc(subtitle)}</div></div></div>',
                    unsafe_allow_html=True)
        yield

"""
utils/style.py
--------------
ALL look-and-feel lives here, so every page looks the same ("Sage Field" theme: ivory-sage
background, white cards with a thin green-grey border, dark forest-green text, green / yellow /
coral status colours and one accent colour per algorithm). The farmer pages add their own
components in utils/farm_ui.py.

What is in this file (top to bottom):
  1. Design tokens         - colours, algorithm accents, chart palettes, fonts
                             (+ the old names pages import, with new values).
  2. Crop names            - crop_title() and crop_emoji() for display (data stays lowercase).
  3. Navigation            - which sidebar group and dot colour every page has.
  4. The CSS               - one stylesheet, split into labelled sections.
  5. apply_style()         - injects the CSS and draws the sidebar (brand + current assessment).
  6. page_header()         - breadcrumb + eyebrow + title + subtitle at the top of each page.
  7. style_fig()           - gives every Plotly chart the same look (neon on navy).
  8. show_chart() / show_table() - draw a chart (inside a card) / table full width.
  9. Reusable HTML helpers - kpi_card, kpi_tile, info_card, result_card, outcome_card, badge,
                             chip, step_flow, score_bar, level_meter, feature_tile, timeline,
                             rule_card, star_schema. They RETURN an HTML string; show it with
                             render_html(html) or st.markdown(html, unsafe_allow_html=True).
 10. dash_card()           - a dashboard card (title, subtitle, coloured top edge, link).

The base theme (colours, fonts, alert colours) comes from .streamlit/config.toml and
uses the same values as the tokens below.
"""
import html as _html
from contextlib import contextmanager

import streamlit as st

from core.crops import CROP_LIST, CROPS_BY_KEY, FAMILIES
from core.features import NAME as FEATURE_NAME

# =============================================================================
# 1. DESIGN TOKENS
# =============================================================================
BG = "#F5F6F4"           # page background (measured from the reference design)
SIDEBAR = "#EBF4E9"      # light sage sidebar
SURFACE = "#FFFFFF"      # cards
SURFACE_2 = "#F3F7F2"    # sunken areas, table headers, tracks
LINE = "#E6ECE5"         # 1px card borders
INK = "#061326"          # headings and body text: near-black navy (17:1 on white)
INK_2 = "#556D84"        # muted text, subtitles (5.3:1 on white)
INK_3 = "#647B8A"        # faint text (4.5:1 on white)
FOREST = "#22A75D"       # primary green: status, accents
FOREST_DEEP = "#0A6A44"  # dark green for text on light
SAGE_SOFT = "#E3F1E6"    # success tint
CLAY = "#E39A2D"         # amber accent: highlights
CLAY_INK = "#8A5A00"     # amber for text
WHEAT = "#FFC72D"
WHEAT_TINT = "#FFF3D5"
SLATE = "#5B9BD5"
SLATE_TINT = "#E6F0FA"
BRICK = "#FF6971"
BRICK_TINT = "#FFE1DD"
MINT = "#2FB573"         # success
GRID = "#ECF0EC"         # chart gridlines

# Pastel summary cards on Home and the status colours used everywhere:
# green = good, yellow = moderate / caution, coral = needs attention (bar colours measured from the design).
KPI_BLUE = "#058A5A"     # kept for old imports: the primary button green
KPI_GREEN = "#EDF6EC"
KPI_ORANGE = "#F9F3E2"
KPI_CYAN = "#FCECE6"
STATUS_GOOD = "#2FB573"
STATUS_MODERATE = "#FFC72D"
STATUS_BAD = "#FF6971"

# One accent per algorithm: its dashboard card, its charts and its page header.
ALGO = {
    "id3": "#B88400",
    "naive_bayes": "#D9548F",
    "regression": "#1F9C8F",
    "kmeans": "#2F86C8",
    "hierarchical": "#4C8FC9",
    "apriori": "#8467D0",
    "fpgrowth": "#A24FC4",
    # pages that are not one algorithm
    "soil": "#3D86C6",
    "whatif": "#DD7430",
    "olap": "#2E9E6A",
    "lake": "#1596AD",
    "prep": "#6FA524",
}

# Old names, kept so every page import keeps working (the values are the navy ones).
PRIMARY = FOREST
DEEP = FOREST_DEEP
LIGHT = SAGE_SOFT
SOFT = SURFACE_2
ACCENT = CLAY
TEXT = INK
BORDER = LINE
MUTED = INK_2
AMBER = WHEAT

# Categorical chart colours (clusters, grouped bars): neon on navy. The first five are
# far apart in hue AND brightness, so small k stays readable for colour-blind viewers.
PALETTE = ["#3D86C6", "#E0649A", "#E3A92B", "#2E9E6A", "#8467D0",
           "#E8793A", "#1F9C8F", "#D9594C", "#6A78D6", "#7DB02E"]

# Continuous values (heat maps, colour bars): card navy -> blue -> cyan -> ice
SEQ_SCALE = [[0.0, "#F1F6EC"], [0.35, "#BFE3C8"], [0.7, "#3FA56B"], [1.0, "#14532D"]]
GREEN_SCALE = SEQ_SCALE   # old name
# Two-sided values (correlations): pink <- navy -> cyan
DIVERGING_SCALE = [[0.0, "#E0649A"], [0.5, "#FFFFFF"], [1.0, "#2E8F6B"]]

FONT_STACK = "Inter, 'Noto Sans Devanagari', 'Mangal', system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
HEADING_STACK = "Inter, 'Noto Sans Devanagari', 'Mangal', system-ui, -apple-system, 'Segoe UI', sans-serif"
SERIF_STACK = HEADING_STACK   # old name: headings used a serif in the previous theme
MONO_STACK = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"


def rgba(hex_color: str, alpha: float) -> str:
    """'#3B82F6', 0.2 -> 'rgba(47, 143, 91, 0.2)' (for glows and gradient fills)."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"


# =============================================================================
# 2. CROP NAMES (display only; the data keeps its lowercase labels)
# =============================================================================
_CROP_EMOJI = {
    "rice": "🌾", "maize": "🌽", "banana": "🍌", "mango": "🥭", "grapes": "🍇",
    "watermelon": "🍉", "muskmelon": "🍈", "apple": "🍎", "orange": "🍊",
    "coconut": "🥥", "coffee": "☕", "kidneybeans": "🫘",
}


def crop_title(crop) -> str:
    """'kidneybeans' -> 'Kidney Beans', 'rice' -> 'Rice'."""
    name = str(crop)
    return CROPS_BY_KEY[name].label if name in CROPS_BY_KEY else name.replace("_", " ").title()


def crop_emoji(crop) -> str:
    """An emoji for the crop, or a neutral seedling when there is no good one."""
    return _CROP_EMOJI.get(str(crop), "🌱")


# Crop families, used only to colour charts (display grouping, not part of any model).
CROP_GROUPS = {family: [c.key for c in CROP_LIST if c.family == family] for family in FAMILIES}   # from core/crops.py
_GROUP_OF = {c.key: c.family for c in CROP_LIST}


def crop_group(crop) -> str:
    """'rice' -> 'Cereals'; crops not in the list -> 'Other'."""
    return _GROUP_OF.get(str(crop), "Other")


# =============================================================================
# 3. NAVIGATION (sidebar group + dot colour of every page)
# =============================================================================
# page file stem -> (sidebar group, accent colour). app.py builds the navigation from
# this, and the CSS below draws a small dot in that colour in front of each link.
NAV_GROUPS = ["Dashboard", "Assess", "Mine", "Data"]
NAV = {
    "2_Soil_Analysis": ("Assess", ALGO["soil"]),
    "3_Crop_Advisor": ("Assess", ALGO["id3"]),
    "4_What-if_Lab": ("Assess", ALGO["whatif"]),
    "5_Pattern_Mining": ("Mine", ALGO["apriori"]),
    "6_Cluster_Explorer": ("Mine", ALGO["kmeans"]),
    "7_Data_Insights": ("Data", ALGO["olap"]),
    "8_Model_Council": ("Assess", ALGO["naive_bayes"]),
    "9_Water_Lab": ("Assess", ALGO["regression"]),
    "10_Hierarchical": ("Mine", ALGO["hierarchical"]),
    "11_FP-Growth_and_Eclat": ("Mine", ALGO["fpgrowth"]),
    "12_Data_Lake": ("Data", ALGO["lake"]),
    "13_Data_Prep": ("Data", ALGO["prep"]),
}
DASHBOARD_DOT = FOREST


def page_number(stem: str) -> int:
    """'10_Hierarchical' -> 10, so pages sort 2, 3, ... 10 (not '10' before '2')."""
    head = stem.split("_", 1)[0]
    return int(head) if head.isdigit() else 999


def page_title(stem: str) -> str:
    """'11_FP-Growth_and_Eclat' -> 'FP-Growth and Eclat'."""
    return stem.split("_", 1)[1].replace("_", " ") if "_" in stem else stem


def page_slug(stem: str) -> str:
    """URL of a page: '4_What-if_Lab' -> 'what-if-lab'. Also used by the CSS dot rules."""
    return page_title(stem).lower().replace(" ", "-")


# =============================================================================
# 4. CSS
# =============================================================================
# Step A: CSS variables, so the rest of the CSS can say var(--am-ink).
_CSS_VARS = f"""
:root {{
  --am-bg: {BG}; --am-sidebar: {SIDEBAR}; --am-surface: {SURFACE}; --am-surface-2: {SURFACE_2};
  --am-line: {LINE}; --am-ink: {INK}; --am-ink-2: {INK_2}; --am-ink-3: {INK_3};
  --am-blue: {FOREST}; --am-blue-ink: {FOREST_DEEP}; --am-btn: #058A5A;
  --am-clay: {CLAY}; --am-clay-ink: {CLAY_INK}; --am-mint: {MINT};
  --am-wheat: {WHEAT}; --am-wheat-tint: {WHEAT_TINT};
  --am-slate: {SLATE}; --am-slate-tint: {SLATE_TINT};
  --am-brick: {BRICK}; --am-brick-tint: {BRICK_TINT}; --am-sage-soft: {SAGE_SOFT};
  --am-shadow: 0 1px 2px rgba(30, 58, 43, 0.05), 0 6px 20px rgba(30, 58, 43, 0.07);
  --am-glow: 0 0 0 1px rgba(47, 143, 91, 0.28), 0 10px 28px rgba(47, 143, 91, 0.14);
  --am-good: {STATUS_GOOD}; --am-moderate: {STATUS_MODERATE}; --am-bad: {STATUS_BAD};
  --am-radius: 16px;
  --am-font: {FONT_STACK}; --am-head: {HEADING_STACK}; --am-mono: {MONO_STACK};
  --accent: {FOREST};
}}
"""

# Step B: the stylesheet itself (a plain string, so CSS braces need no escaping).
_CSS_BODY = """
/* ---------- 4.1 Page base --------------------------------------------------- */
.stApp { background: radial-gradient(900px 500px at 90% -10%, rgba(143, 200, 150, 0.22), transparent 60%),
                     radial-gradient(700px 400px at -5% 100%, rgba(233, 185, 73, 0.10), transparent 60%),
                     var(--am-bg); }
.block-container, [data-testid="stMainBlockContainer"] {
  padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1320px;
}
.stApp :is(p, li) { line-height: 1.6; }
[data-testid="stCaptionContainer"], .stApp small { color: var(--am-ink-2); font-size: 0.86rem; line-height: 1.5; }
.stApp :is(h1, h2, h3, h4) { color: var(--am-ink); letter-spacing: -0.015em; font-family: var(--am-head); }
.stApp h3 { margin-top: 1.4rem; }
/* Numbers line up in columns */
[data-testid="stMetricValue"], .am-num, .kpi-value, .result-value, .tile-value, .score-pct {
  font-variant-numeric: tabular-nums;
}
/* Never touch icon fonts (expander arrows, sidebar chevrons, nav icons). */
.stApp :is([data-testid="stIconMaterial"], .material-icons, .material-symbols-rounded,
           [class*="material-symbols"]) {
  font-family: "Material Symbols Rounded", "Material Icons" !important;
}

/* Gentle entrance for the page content */
@keyframes am-rise { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
[data-testid="stMainBlockContainer"] { animation: am-rise 0.28s ease-out both; }
@media (prefers-reduced-motion: reduce) {
  .stApp *, .stApp *::before, .stApp *::after { animation: none !important; transition: none !important; }
}

/* ---------- 4.2 Page header (page_header) ----------------------------------- */
.am-header { position: relative; padding: 0 0 1.1rem 0; margin: 0 0 1.4rem 0;
             border-bottom: 1px solid var(--am-line); }
.am-header::after { content: ""; position: absolute; left: 0; bottom: -1px; width: 96px; height: 2px;
                    background: var(--accent); border-radius: 2px; box-shadow: 0 0 12px var(--accent); }
.am-crumbs { color: var(--am-ink-3); font-size: 0.8rem; font-weight: 500; margin-bottom: 0.55rem; }
.am-crumbs span + span::before { content: "/"; margin: 0 0.45rem; color: var(--am-line); }
.am-crumbs span:last-child { color: var(--am-ink-2); }
.am-eyebrow { display: inline-flex; align-items: center; gap: 0.5rem;
              color: var(--accent); font-size: 0.72rem; font-weight: 700; letter-spacing: 0.14em;
              text-transform: uppercase; }
.am-eyebrow::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--accent);
                      box-shadow: 0 0 10px var(--accent); }
.am-title { font-family: var(--am-head); color: var(--am-ink); font-size: 2.3rem;
            font-weight: 700; letter-spacing: -0.03em; line-height: 1.12; margin-top: 0.35rem; }
.am-subtitle { color: var(--am-ink-2); font-size: 1rem; line-height: 1.55; margin-top: 0.4rem; max-width: 50rem; }

/* ---------- 4.3 Sidebar ----------------------------------------------------- */
[data-testid="stSidebar"] { background: var(--am-sidebar); border-right: 1px solid var(--am-line); }
[data-testid="stSidebarContent"] { display: flex; flex-direction: column; }
/* Lift our own sidebar blocks out of their wrappers so they can sit around the nav:
   brand (order 1) -> navigation (2) -> current assessment (3, pushed to the bottom) -> footer (4). */
[data-testid="stSidebarUserContent"],
[data-testid="stSidebarUserContent"] > div,
[data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"],
[data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] { display: contents; }
[data-testid="stSidebarHeader"] { order: 0; height: 2.6rem; min-height: 0; padding-bottom: 0; }
.st-key-am_brand, .st-key-am_side_assess { flex: 0 0 auto; }
.st-key-am_brand { order: 1; padding: 0 0 1rem 0; margin-top: -1.9rem; }
.st-key-am_side_assess { order: 3; margin-top: auto; padding: 1.2rem 0 0 0; }
[data-testid="stSidebar"] { min-width: 17rem; }
[data-testid="stSidebarNavSeparator"] { display: none; }
/* Brand */
.brand-row { display: flex; align-items: center; gap: 0.6rem; }
.brand-logo { width: 32px; height: 32px; flex-shrink: 0; filter: drop-shadow(0 2px 6px rgba(30, 127, 72, 0.3)); }
.brand-name { font-family: var(--am-head); color: var(--am-ink); font-size: 1.45rem; font-weight: 700;
              letter-spacing: -0.03em; line-height: 1; }
.brand-tag { color: var(--am-ink-3); font-size: 0.64rem; font-weight: 600; letter-spacing: 0.06em;
             margin: 0.45rem 0 0 0; text-transform: uppercase; }
/* Navigation: group headers + links with a coloured dot */
[data-testid="stNavSectionHeader"] {
  color: var(--am-ink-3); font-size: 0.66rem; font-weight: 700; letter-spacing: 0.16em;
  text-transform: uppercase; margin-top: 0.7rem;
}
[data-testid="stSidebarNavLink"] {
  position: relative; border-radius: 10px; margin: 1px 0; min-height: 1.95rem;
  transition: background 0.15s ease, box-shadow 0.15s ease;
}
[data-testid="stSidebarNavLink"]::before {
  content: ""; flex: 0 0 8px; width: 8px; height: 8px; border-radius: 50%; margin: 0 0.7rem 0 0.15rem;
  align-self: center; background: var(--dot, var(--am-blue)); box-shadow: 0 0 8px var(--dot, var(--am-blue));
}
[data-testid="stSidebarNavLink"] :is(span, p) { color: var(--am-ink-2); font-weight: 500; }
/* Label on one centre line with the dot */
[data-testid="stSidebarNavLink"] [data-testid="stMarkdownContainer"] { display: flex; align-items: center; height: 100%; }
[data-testid="stSidebarNavLink"] p { display: block; line-height: 1.25rem; margin: 0; }
[data-testid="stSidebarNavLink"]:hover { background: rgba(47, 143, 91, 0.10); }
[data-testid="stSidebarNavLink"]:hover :is(span, p) { color: var(--am-ink); }
/* Active page: blue tint and a blue bar on the left edge */
[data-testid="stSidebarNavLink"][aria-current="page"] {
  background: rgba(47, 143, 91, 0.16); box-shadow: inset 3px 0 0 var(--am-blue);
}
[data-testid="stSidebarNavLink"][aria-current="page"] :is(span, p) { color: var(--am-ink); font-weight: 600; }
/* Current assessment mini-card */
.side-card { background: var(--am-surface); border: 1px solid var(--am-line); border-radius: 12px;
             padding: 0.8rem 0.9rem; box-shadow: inset 0 2px 0 var(--am-clay); }
.side-label { color: var(--am-ink-3); font-size: 0.66rem; font-weight: 700; letter-spacing: 0.14em;
              text-transform: uppercase; display: flex; justify-content: space-between; }
.side-crop { font-family: var(--am-head); color: var(--am-ink); font-size: 1.15rem; font-weight: 600;
             margin-top: 0.35rem; }
.side-values { color: var(--am-ink-2); font-size: 0.78rem; margin-top: 0.25rem; line-height: 1.45; }
.side-empty { color: var(--am-ink-2); font-size: 0.82rem; margin-top: 0.35rem; }
.st-key-am_side_assess [data-testid="stPageLink"] { margin-top: 1.25rem; }

/* ---------- 4.4 Cards: one style ------------------------------------------- */
.am-card, [data-testid="stForm"], [class*="st-key-am_card"] {
  background: var(--am-surface); border: 1px solid var(--am-line); border-radius: var(--am-radius);
  box-shadow: var(--am-shadow); transition: box-shadow 0.2s ease, border-color 0.2s ease;
}
.am-card:hover, [class*="st-key-am_card"]:hover { box-shadow: var(--am-glow); border-color: #B9D3BE; }
.am-card { padding: 1.1rem 1.3rem; }
[data-testid="stForm"] { padding: 1.4rem 1.6rem 1.2rem 1.6rem; }
[class*="st-key-am_card"] { padding: 1.1rem 1.25rem; }
/* Charts sit inside a card (see show_chart) */
[class*="st-key-am_chart"] {
  background: var(--am-surface); border: 1px solid var(--am-line); border-radius: var(--am-radius);
  box-shadow: var(--am-shadow); padding: 0.8rem 0.9rem 0.4rem 0.9rem;
}
/* Bordered st.container(border=True) */
[data-testid="stVerticalBlock"][class*="BorderWrapper"], [data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--am-surface); border-color: var(--am-line); border-radius: var(--am-radius);
}

/* ---------- 4.5 Dashboard cards (dash_card) -------------------------------- */
[class*="st-key-am_dash_"] {
  position: relative; background: var(--am-surface); border: 1px solid var(--am-line);
  border-radius: var(--am-radius); padding: 1rem 1.1rem 0.7rem 1.1rem; box-shadow: var(--am-shadow);
  overflow: hidden; height: 100%; transition: box-shadow 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
}
[class*="st-key-am_dash_"]::before {   /* coloured top edge */
  content: ""; position: absolute; left: 0; right: 0; top: 0; height: 3px; background: var(--accent);
  box-shadow: 0 0 14px var(--accent);
}
[class*="st-key-am_dash_"]:hover { border-color: #B9D3BE; box-shadow: var(--am-glow); transform: translateY(-1px); }
/* Charts inside a dashboard card need no second card around them */
[class*="st-key-am_dash_"] [class*="st-key-am_chart"] { background: transparent; border: 0; box-shadow: none; padding: 0; }
.dash-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 0.6rem; }
.dash-head > div:first-child { min-width: 0; flex: 1 1 auto; }
/* Cards in one row stretch to the same height */
[data-testid="stHorizontalBlock"]:has([class*="st-key-am_dash_"]) { align-items: stretch; }
[data-testid="stColumn"]:has([class*="st-key-am_dash_"]) > [data-testid="stVerticalBlock"],
[data-testid="stColumn"]:has([class*="st-key-am_dash_"]) > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] { height: 100%; }
.dash-title { font-family: var(--am-head); color: var(--am-ink); font-size: 1.05rem; font-weight: 600;
              letter-spacing: -0.01em; display: flex; align-items: center; gap: 0.5rem; }
.dash-title::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: var(--accent);
                      box-shadow: 0 0 10px var(--accent); }
.dash-sub { color: var(--am-ink-2); font-size: 0.82rem; margin-top: 0.15rem; line-height: 1.4; min-height: 2.8em;
            display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.dash-tag { color: var(--accent); background: var(--am-surface-2); border: 1px solid var(--am-line);
            border-radius: 999px; padding: 0.08rem 0.55rem; font-size: 0.7rem; font-weight: 700; white-space: nowrap;
            flex: 0 0 auto; }
[class*="st-key-am_dash_"] [data-testid="stPageLink"] a { padding: 0.1rem 0; background: transparent; }
[class*="st-key-am_dash_"] [data-testid="stPageLink"] a p { color: var(--am-blue-ink); font-size: 0.82rem; font-weight: 600; }
[class*="st-key-am_dash_"] [data-testid="stPageLink"] a:hover p { color: var(--am-ink); }

/* ---------- 4.6 KPI tiles (kpi_tile: solid colour + white sparkline) ------- */
.kpi-solid { position: relative; overflow: hidden; border-radius: var(--am-radius); padding: 1rem 1.15rem 0.85rem 1.15rem;
             color: #FFFFFF; height: 100%; box-shadow: 0 10px 30px rgba(30, 58, 43, 0.18);
             transition: transform 0.2s ease, box-shadow 0.2s ease; }
.kpi-solid:hover { transform: translateY(-2px); box-shadow: 0 14px 36px rgba(30, 58, 43, 0.25); }
.kpi-solid::after { content: ""; position: absolute; right: -40px; top: -60px; width: 160px; height: 160px; border-radius: 50%;
                    background: rgba(255, 255, 255, 0.08); pointer-events: none; }
.kpi-solid .kpi-label { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase;
                        color: rgba(255, 255, 255, 0.92); }
.kpi-solid .kpi-big { font-family: var(--am-head); font-size: 2.05rem; font-weight: 700; letter-spacing: -0.03em;
                      line-height: 1.15; margin-top: 0.25rem; font-variant-numeric: tabular-nums; color: #FFFFFF; }
.kpi-solid .kpi-note { font-size: 0.8rem; color: #FFFFFF; opacity: 0.92; margin-top: 0.1rem;
                       white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.kpi-spark { display: block; width: 100%; height: 38px; margin-top: 0.55rem; }

/* ---------- 4.7 Metric tiles (st.metric) ----------------------------------- */
[data-testid="stMetric"] {
  background: var(--am-surface); border: 1px solid var(--am-line); border-radius: var(--am-radius);
  padding: 1rem 1.2rem 0.9rem 1.2rem; box-shadow: var(--am-shadow); height: 100%;
}
[data-testid="stMetricLabel"] :is(p, div) {
  color: var(--am-ink-2); font-size: 0.72rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
}
[data-testid="stMetricValue"] {
  font-family: var(--am-head); color: var(--am-ink); font-size: 2rem; font-weight: 700; letter-spacing: -0.02em;
}

/* ---------- 4.8 Buttons and page links ------------------------------------- */
[data-testid^="stBaseButton-"]:not([data-testid="stBaseButton-headerNoPadding"]):not([data-testid="stBaseButton-header"]) {
  font-weight: 600; transition: background 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}
:is([data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"]) {
  background: var(--am-btn); border-color: var(--am-btn); color: #FFFFFF;
  box-shadow: 0 6px 18px rgba(30, 127, 72, 0.30);
}
:is([data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"]):hover {
  background: #16693A; border-color: #16693A; color: #FFFFFF; box-shadow: 0 8px 24px rgba(30, 127, 72, 0.4);
}
:is([data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-secondaryFormSubmit"]) {
  background: var(--am-surface); border-color: var(--am-line); color: var(--am-ink);
}
:is([data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-secondaryFormSubmit"]):hover {
  background: #E8F3E4; border-color: var(--am-blue); color: var(--am-ink);
}
[data-testid="stBaseButton-secondary"]:disabled { background: transparent; opacity: 0.5; }
.stApp :is(button, a, input, [role="slider"], [role="tab"]):focus-visible {
  outline: 2px solid var(--am-blue-ink); outline-offset: 2px;
}

/* ---------- 4.9 Inputs ------------------------------------------------------ */
.stApp :is([data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"]) {
  background-color: var(--am-surface-2); border-color: var(--am-line);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.stApp :is([data-baseweb="input"], [data-baseweb="select"] > div):focus-within {
  border-color: var(--am-blue); box-shadow: 0 0 0 3px rgba(47, 143, 91, 0.25);
}
.stApp [data-baseweb="input"] input { background: transparent; }
[data-testid="stNumberInput"] button { background: var(--am-surface-2); }
[data-testid="stNumberInput"] button:hover { background: #E8F3E4; color: var(--am-ink); }
[data-testid="stWidgetLabel"] :is(p, label) { color: var(--am-ink); font-weight: 500; }
/* Multiselect chips */
.stApp [data-baseweb="tag"] { background: rgba(47, 143, 91, 0.16); color: var(--am-ink); border-radius: 8px; }
.stApp [data-baseweb="tag"] span { color: var(--am-ink); }

/* ---------- 4.10 Sliders ---------------------------------------------------- */
.stApp [data-baseweb="slider"] [role="slider"] {
  background: var(--am-ink); border: 2px solid var(--am-blue);
  box-shadow: 0 0 0 4px rgba(47, 143, 91, 0.2); width: 18px; height: 18px;
}
[data-testid="stSliderThumbValue"] { color: var(--am-blue-ink); font-weight: 600; font-variant-numeric: tabular-nums; }
[data-testid="stSliderTickBarMin"], [data-testid="stSliderTickBarMax"] { color: var(--am-ink-3); }

/* ---------- 4.11 Tabs: segmented control ----------------------------------- */
[data-testid="stTabs"] [role="tablist"] {
  background: var(--am-surface-2); border: 1px solid var(--am-line); border-radius: 12px; padding: 4px; gap: 4px;
  width: fit-content; max-width: 100%; overflow-x: auto;
}
[data-testid="stTabs"] [role="tablist"]::after, [data-testid="stTabs"] .react-aria-SelectionIndicator { display: none; }
[data-testid="stTab"] {
  border-radius: 9px; padding: 0.4rem 1.05rem; height: auto; background: transparent; margin: 0;
  transition: background 0.15s ease, box-shadow 0.15s ease;
}
[data-testid="stTab"] p { color: var(--am-ink-2); font-weight: 500; margin: 0; }
[data-testid="stTab"]:hover p { color: var(--am-ink); }
[data-testid="stTab"][aria-selected="true"] { background: var(--am-btn); box-shadow: 0 4px 14px rgba(30, 127, 72, 0.30); }
[data-testid="stTab"][aria-selected="true"] p { color: #FFFFFF; font-weight: 600; }
[data-testid="stTabPanel"] { padding-top: 1rem; }

/* ---------- 4.12 Expanders and popovers ------------------------------------ */
[data-testid="stExpander"] details {
  background: var(--am-surface); border: 1px solid var(--am-line); border-radius: var(--am-radius);
  box-shadow: var(--am-shadow); overflow: hidden;
}
[data-testid="stExpander"] summary:hover { background: #E8F3E4; }
[data-testid="stExpander"] summary p { font-weight: 600; color: var(--am-ink); }
[data-testid="stPopoverBody"] { border-radius: 12px; border: 1px solid var(--am-line); max-width: 30rem; background: var(--am-surface); }

/* ---------- 4.13 Alerts ----------------------------------------------------- */
[data-testid="stAlert"] [data-testid="stAlertContainer"], [data-testid="stAlertContainer"] { border-radius: 12px; }

/* ---------- 4.14 Tables and code ------------------------------------------- */
[data-testid="stDataFrame"], [data-testid="stTable"] {
  border-radius: 12px; overflow: hidden; box-shadow: var(--am-shadow); background: var(--am-surface);
  border: 1px solid var(--am-line);
}
[data-testid="stCode"] pre { border-radius: 12px; padding: 1rem 1.1rem; border: 1px solid var(--am-line); }
/* Syntax colours readable on the dark code panel */
[data-testid="stCode"] .token.keyword { color: #8A44B8; }
[data-testid="stCode"] .token:is(.string, .attr-value) { color: #1B7F46; }
[data-testid="stCode"] .token:is(.number, .boolean) { color: #A45A06; }
[data-testid="stCode"] .token:is(.function, .class-name) { color: #1F6FB0; }
[data-testid="stCode"] .token:is(.operator, .punctuation) { color: #4A6455; }
[data-testid="stCode"] .token.comment { color: #62796B; }
[data-testid="stCode"] code { color: #1E3A2B; }

/* ---------- 4.15 Small building blocks ------------------------------------- */
.am-label { color: var(--am-ink-2); font-size: 0.72rem; font-weight: 700; letter-spacing: 0.1em;
            text-transform: uppercase; }
.am-section-note { color: var(--am-ink-2); font-size: 0.88rem; margin: -0.3rem 0 0.8rem 0; }
.chip { display: inline-flex; align-items: center; gap: 0.3rem; background: var(--am-surface-2);
        border: 1px solid var(--am-line); border-radius: 999px; padding: 0.15rem 0.7rem;
        font-size: 0.8rem; font-weight: 500; color: var(--am-ink); white-space: nowrap; }
.chip b { color: var(--am-ink-2); font-weight: 500; }
.chip-crop { background: rgba(46, 158, 106, 0.12); border-color: rgba(46, 158, 106, 0.4); color: #1F6B42; font-weight: 600; }
.badge { display: inline-block; border-radius: 999px; padding: 0.1rem 0.6rem; font-size: 0.74rem;
         font-weight: 600; letter-spacing: 0.01em; border: 1px solid transparent; white-space: nowrap; }
.badge-neutral { background: var(--am-surface-2); color: var(--am-ink-2); border-color: var(--am-line); }
.badge-success { background: rgba(46, 158, 106, 0.12); color: #1F6B42; border-color: rgba(46, 158, 106, 0.4); }
.badge-info    { background: rgba(61, 134, 198, 0.12); color: #1F6FB0; border-color: rgba(61, 134, 198, 0.4); }
.badge-warning { background: rgba(227, 169, 43, 0.14); color: #7A5200; border-color: rgba(227, 169, 43, 0.45); }
.badge-danger  { background: rgba(224, 100, 79, 0.12); color: #B0382A; border-color: rgba(224, 100, 79, 0.4); }
.badge-accent  { background: rgba(227, 154, 45, 0.16); color: var(--am-clay-ink); border-color: rgba(227, 154, 45, 0.5); }

/* KPI tile (plain, on a card) */
.kpi { background: var(--am-surface); border: 1px solid var(--am-line); border-radius: var(--am-radius);
       padding: 1rem 1.2rem; box-shadow: var(--am-shadow); height: 100%; }
.kpi-value { font-family: var(--am-head); color: var(--am-ink); font-size: 1.9rem; font-weight: 700;
             letter-spacing: -0.02em; line-height: 1.25; margin-top: 0.2rem; }
.kpi-hint { color: var(--am-ink-2); font-size: 0.8rem; margin-top: 0.15rem; }

/* Info card */
.info-card { background: var(--am-surface); border: 1px solid var(--am-line); border-radius: var(--am-radius);
             padding: 1rem 1.2rem; height: 100%; }
.info-card-title { color: var(--am-ink); font-size: 0.98rem; font-weight: 600; margin-bottom: 0.25rem; }
.info-card-body { color: var(--am-ink-2); font-size: 0.9rem; line-height: 1.55; }

/* Result card (the main answer) */
.result-card { position: relative; overflow: hidden; background: var(--am-surface);
               border: 1px solid var(--am-line); border-radius: 18px; padding: 1.5rem 1.6rem;
               box-shadow: var(--am-shadow); height: 100%; }
.result-card::before { content: ""; position: absolute; left: 0; right: 0; top: 0; height: 3px; background: var(--accent);
                       box-shadow: 0 0 14px var(--accent); }
.result-card::after { content: ""; position: absolute; right: -80px; top: -80px; width: 260px; height: 260px; border-radius: 50%;
                      background: radial-gradient(circle, rgba(47, 143, 91, 0.14), transparent 70%); pointer-events: none; }
.result-top { display: flex; align-items: center; gap: 1.1rem; }
.result-emoji { width: 64px; height: 64px; border-radius: 16px; background: var(--am-surface-2); border: 1px solid var(--am-line);
                display: grid; place-items: center; font-size: 2.1rem; flex-shrink: 0; }
.result-value { font-family: var(--am-head); color: var(--am-ink); font-size: 2.6rem; font-weight: 700;
                letter-spacing: -0.03em; line-height: 1.05; margin-top: 0.15rem; }
.result-sub { position: relative; color: var(--am-ink-2); font-size: 0.88rem; margin-top: 0.9rem; }
.result-body { position: relative; margin-top: 0.9rem; }

/* Outcome card (What-if before / after) */
.outcome { background: var(--am-surface); border: 1px solid var(--am-line); border-radius: var(--am-radius);
           padding: 1.1rem 1.2rem; box-shadow: var(--am-shadow); height: 100%; }
.outcome-hit { border-color: rgba(46, 158, 106, 0.55); background: linear-gradient(180deg, rgba(46, 158, 106, 0.12) 0%, var(--am-surface) 70%); }
.outcome-crop { display: flex; align-items: center; gap: 0.5rem; font-family: var(--am-head);
                color: var(--am-ink); font-size: 1.6rem; font-weight: 700; letter-spacing: -0.02em; margin: 0.35rem 0 0.7rem 0; }
.outcome-row { display: flex; justify-content: space-between; align-items: center; padding: 0.42rem 0;
               border-top: 1px solid var(--am-line); font-size: 0.88rem; color: var(--am-ink-2); }
.outcome-row b { color: var(--am-ink); font-weight: 600; }
.outcome-arrow { display: grid; place-items: center; height: 100%; min-height: 120px; color: var(--am-clay);
                 font-size: 1.6rem; }

/* Step flow: chip -> chip -> chip */
.step-flow { display: flex; flex-wrap: wrap; align-items: center; gap: 0.4rem; }
.step-chip { background: var(--am-surface); border: 1px solid var(--am-line); border-radius: 999px;
             padding: 0.3rem 0.85rem; font-size: 0.86rem; font-weight: 500; color: var(--am-ink); }
.step-chip b { color: var(--accent); margin-right: 0.35rem; }
.step-arrow { color: var(--am-ink-3); }

/* Score bar */
.score { margin: 0.45rem 0; }
.score-head { display: flex; justify-content: space-between; font-size: 0.84rem; margin-bottom: 0.3rem; }
.score-label { color: var(--am-ink-2); }
.score-pct { color: var(--am-ink); font-weight: 600; }
.score-track { background: var(--am-surface-2); border: 1px solid var(--am-line); border-radius: 999px; height: 8px; overflow: hidden; }
.score-fill { background: linear-gradient(90deg, #16693A, var(--am-blue)); height: 100%; border-radius: 999px; }
.score-fill.clay { background: linear-gradient(90deg, #B45309, var(--am-clay)); }

/* Level meter: low / medium / high in three segments */
.meter { display: grid; grid-template-columns: repeat(3, 1fr); gap: 3px; margin-top: 0.7rem; }
.meter span { height: 5px; border-radius: 999px; background: var(--am-surface-2); }
.meter span.on { background: var(--accent); box-shadow: 0 0 8px var(--accent); }
.meter-legend { display: grid; grid-template-columns: repeat(3, 1fr); margin-top: 0.3rem;
                font-size: 0.68rem; color: var(--am-ink-3); letter-spacing: 0.04em; }
.meter-legend span.on { color: var(--am-ink); font-weight: 600; }
.meter-legend span:nth-child(2) { text-align: center; }
.meter-legend span:nth-child(3) { text-align: right; }

/* Feature tile (Soil Analysis) */
.tile { background: var(--am-surface); border: 1px solid var(--am-line); border-radius: var(--am-radius);
        padding: 0.95rem 1.1rem 0.85rem 1.1rem; box-shadow: var(--am-shadow); height: 100%; cursor: help;
        transition: box-shadow 0.2s ease, border-color 0.2s ease; }
.tile:hover { box-shadow: var(--am-glow); border-color: #B9D3BE; }
.tile-head { display: flex; justify-content: space-between; align-items: center; gap: 0.4rem; }
.tile-value { font-family: var(--am-head); color: var(--am-ink); font-size: 1.75rem; font-weight: 700;
              letter-spacing: -0.02em; margin-top: 0.3rem; line-height: 1.15; }
.tile-value small { font-family: var(--am-font); font-size: 0.8rem; color: var(--am-ink-2); font-weight: 500;
                    margin-left: 0.25rem; letter-spacing: 0; }

/* Timeline (ID3 decision path) */
.timeline { position: relative; margin: 0.3rem 0 0 0; padding: 0; list-style: none; }
.tl-step { position: relative; display: grid; grid-template-columns: 2.2rem 1fr; gap: 0.9rem; padding-bottom: 1rem; }
.tl-step::before { content: ""; position: absolute; left: calc(1.1rem - 1px); top: 2.2rem; bottom: 0;
                   width: 2px; background: linear-gradient(180deg, var(--accent), var(--am-line)); }
.tl-dot { width: 2.2rem; height: 2.2rem; border-radius: 50%; background: var(--am-surface);
          border: 1.5px solid var(--accent); color: var(--accent); display: grid; place-items: center;
          font-weight: 700; font-size: 0.85rem; font-variant-numeric: tabular-nums; box-shadow: 0 0 10px rgba(227, 169, 43, 0.3); }
.tl-body { background: var(--am-surface); border: 1px solid var(--am-line); border-radius: 12px;
           padding: 0.7rem 0.95rem; box-shadow: var(--am-shadow); }
.tl-title { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; color: var(--am-ink);
            font-weight: 600; font-size: 0.95rem; }
.tl-meta { color: var(--am-ink-2); font-size: 0.82rem; margin-top: 0.2rem; }
.tl-gain { display: grid; grid-template-columns: 6.5rem 1fr 3.2rem; align-items: center; gap: 0.6rem;
           margin-top: 0.45rem; font-size: 0.78rem; color: var(--am-ink-2); }
.tl-gain .score-track { height: 6px; }
.tl-gain .score-fill { background: var(--accent); }
.tl-gain b { color: var(--am-ink); font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; }
.tl-end { margin-bottom: 1rem; }
.tl-end .tl-step { padding-bottom: 0; }
.tl-end .tl-step::before { display: none; }
.tl-end .tl-dot { background: var(--accent); color: #1E3A2B; font-size: 1rem; }
.tl-end .tl-body { background: rgba(227, 169, 43, 0.10); border-color: rgba(227, 169, 43, 0.45); box-shadow: none; }

/* Rule card (Apriori) */
.rule { display: flex; flex-direction: column; position: relative; overflow: hidden; background: var(--am-surface);
        border: 1px solid var(--am-line); border-radius: var(--am-radius); padding: 1rem 1.15rem 0.95rem 1.15rem;
        box-shadow: var(--am-shadow); height: 100%; transition: box-shadow 0.2s ease, border-color 0.2s ease; }
.rule::before { content: ""; position: absolute; left: 0; right: 0; top: 0; height: 3px; background: var(--accent); }
.rule:hover { box-shadow: var(--am-glow); border-color: #B9D3BE; }
.rule-rank { color: var(--accent); font-size: 0.72rem; font-weight: 700; letter-spacing: 0.12em;
             text-transform: uppercase; margin-bottom: 0.25rem; }
/* IF / THEN in a fixed first column, chips wrap inside the second column */
.rule-row { display: grid; grid-template-columns: 2.6rem minmax(0, 1fr); align-items: start; margin-top: 0.5rem; }
.rule-row .rule-kw { line-height: 1.6rem; }
.rule-chips { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.rule-chips .chip { line-height: 1.3rem; }
.rule-line { display: flex; flex-wrap: wrap; align-items: center; gap: 0.35rem; margin-top: 0.55rem; }
.rule-kw { color: var(--am-ink-3); font-size: 0.7rem; font-weight: 700; letter-spacing: 0.12em; margin-right: 0.15rem; }
/* Stats pinned to the bottom, so all three cards end on the same line */
.rule-stats { display: grid; grid-template-columns: repeat(3, auto); justify-content: space-between; gap: 0.75rem;
              margin-top: auto; padding-top: 0.75rem; border-top: 1px solid var(--am-line); }
.rule-stat span { color: var(--am-ink-2); font-size: 0.76rem; white-space: nowrap; }
.rule-spacer { flex: 0 0 0.9rem; }
.rule-stat b { display: block; font-family: var(--am-head); color: var(--am-ink); font-size: 1.15rem; font-weight: 700;
               font-variant-numeric: tabular-nums; margin-top: 0.1rem; }
.rule-stat b.lift { color: var(--accent); }
/* Equal-height card row: one CSS grid, so every card in a row stretches to the tallest */
.card-grid { display: grid; grid-template-columns: repeat(var(--cols, 3), minmax(0, 1fr)); gap: 1rem; align-items: stretch; }
@media (max-width: 900px) { .card-grid { grid-template-columns: minmax(0, 1fr); } }

/* Star schema diagram (Data Insights) */
.schema { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); grid-template-rows: auto auto auto;
          gap: 0.9rem 1.1rem; align-items: center; position: relative; padding: 0.4rem 0; }
.schema-node { position: relative; z-index: 1; background: var(--am-surface-2); border: 1px solid var(--am-line);
               border-radius: 12px; padding: 0.6rem 0.75rem; text-align: center; }
.schema-node code { all: unset; font-family: var(--am-mono); font-size: 0.72rem; color: var(--am-ink);
                    overflow-wrap: normal; }
.schema-rows { color: var(--am-ink-2); font-size: 0.74rem; margin-top: 0.15rem; font-variant-numeric: tabular-nums; }
.schema-fact { grid-column: 2; grid-row: 2; background: var(--am-btn); border-color: var(--am-blue);
               padding: 0.95rem 0.8rem; box-shadow: 0 0 24px rgba(47, 143, 91, 0.35); }
.schema-fact code { color: #FFFFFF; font-weight: 500; }
.schema-fact .schema-rows { color: rgba(255, 255, 255, 0.9); }
.schema-fact .am-label { color: rgba(255, 255, 255, 0.9); }
.schema-n { grid-column: 2; grid-row: 1; } .schema-s { grid-column: 2; grid-row: 3; }
.schema-w { grid-column: 1; grid-row: 2; } .schema-e { grid-column: 3; grid-row: 2; }
.schema-lines { position: absolute; inset: 0; z-index: 0; }
.schema-lines::before { content: ""; position: absolute; left: 16%; right: 16%; top: 50%; border-top: 1.5px dashed #B8CDBB; }
.schema-lines::after { content: ""; position: absolute; top: 12%; bottom: 12%; left: 50%; border-left: 1.5px dashed #B8CDBB; }

/* Data lake zones (Data Lake page) */
.zone-flow { display: grid; grid-template-columns: 1fr auto 1fr auto 1fr; gap: 0.6rem; align-items: stretch; }
.zone { background: var(--am-surface); border: 1px solid var(--am-line); border-radius: var(--am-radius);
        padding: 0.9rem 1rem; position: relative; overflow: hidden; }
.zone::before { content: ""; position: absolute; left: 0; right: 0; top: 0; height: 3px; background: var(--zone, var(--accent)); }
.zone-name { font-family: var(--am-head); font-weight: 700; color: var(--am-ink); font-size: 1.05rem; }
.zone-body { color: var(--am-ink-2); font-size: 0.84rem; margin-top: 0.25rem; line-height: 1.45; }
.zone-arrow { display: grid; place-items: center; color: var(--am-ink-3); font-size: 1.3rem; }
@media (max-width: 900px) { .zone-flow { grid-template-columns: 1fr; } .zone-arrow { transform: rotate(90deg); } }

/* ---------- 4.16 Clutter ---------------------------------------------------- */
[data-testid="stHeaderActionElements"] { display: none; }
footer { visibility: hidden; height: 0; }
#MainMenu { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }
[data-testid="stHeader"] { background: transparent; }

/* ---------- 4.17 Responsive ------------------------------------------------- */
@media (max-width: 768px) {
  .block-container, [data-testid="stMainBlockContainer"] { padding-left: 1rem; padding-right: 1rem; padding-top: 1.6rem; }
  [data-testid="stHorizontalBlock"] { flex-wrap: wrap; gap: 0.8rem; }
  [data-testid="stColumn"] { min-width: 100% !important; flex: 1 1 100% !important; width: 100% !important; }
  .am-title { font-size: 1.8rem; }
  .result-value { font-size: 2.1rem; }
  .outcome-arrow { min-height: 0; transform: rotate(90deg); }
  .schema { grid-template-columns: 1fr 1fr; }
  .schema-fact { grid-column: 1 / span 2; grid-row: 2; }
  .schema-n { grid-column: 1; grid-row: 1; } .schema-s { grid-column: 2; grid-row: 1; }
  .schema-w { grid-column: 1; grid-row: 3; } .schema-e { grid-column: 2; grid-row: 3; }
  .schema-lines { display: none; }
}
"""


def _nav_dot_css() -> str:
    """One rule per page: the dot in front of its sidebar link gets the page's accent colour."""
    rules = [f'[data-testid="stSidebarNavLink"][href$="/{page_slug(stem)}"] {{ --dot: {color}; }}'
             for stem, (_, color) in NAV.items()]
    return "\n".join(rules) + "\n"


def _build_css() -> str:
    """Join the variables and the stylesheet into one <style> block (fonts come from config.toml)."""
    css = _CSS_VARS + _CSS_BODY + _nav_dot_css()
    # Markdown can be confused by blank lines, so drop them before injecting.
    css = "\n".join(line for line in css.splitlines() if line.strip())
    return f"<style>\n{css}\n</style>"


_CSS = _build_css()

# Inline SVG logo shown next to the brand name (no image file needed): a sprout on a
# blue-to-cyan tile with three "data" dots, so it reads as crops + mining.
_LEAF_SVG = (
    '<svg class="brand-logo" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
    '<defs><linearGradient id="amg" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">'
    f'<stop stop-color="#2F8F5B"/><stop offset="1" stop-color="#7BC47F"/></linearGradient></defs>'
    '<rect width="32" height="32" rx="9" fill="url(#amg)"/>'
    '<path d="M16 25v-8" stroke="#FFFFFF" stroke-width="1.8" stroke-linecap="round"/>'
    '<path d="M16 17c0-4.2 2.8-7 7.5-7 0 4.4-2.9 7-7.5 7z" fill="#FFFFFF"/>'
    '<path d="M16 19.5c0-3.3-2.2-5.5-5.9-5.5 0 3.4 2.3 5.5 5.9 5.5z" fill="#FFFFFF" opacity="0.7"/>'
    f'<circle cx="8" cy="8" r="1.6" fill="{WHEAT}"/><circle cx="12.5" cy="6" r="1.2" fill="{ALGO["naive_bayes"]}"/>'
    f'<circle cx="24.5" cy="24" r="1.4" fill="{WHEAT}"/>'
    '</svg>'
)


# =============================================================================
# 5. apply_style()  (CSS + sidebar)
# =============================================================================
def _esc(value) -> str:
    """Make text safe to place inside our HTML (also stops '$' being read as maths)."""
    return _html.escape(str(value), quote=True).replace("$", "&#36;")


_SIDE_SLOT_KEY = "_am_side_slot"


def apply_style() -> None:
    """Inject the shared CSS and draw the sidebar. Call once at the top of every page."""
    from utils.farm_ui import FARM_CSS, draw_nav, draw_tagline   # local import: farm_ui imports this module

    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown(FARM_CSS, unsafe_allow_html=True)
    with st.sidebar.container(key="am_brand"):
        st.markdown(
            '<div class="brand"><div class="brand-row">' + _LEAF_SVG +
            '<span class="brand-name">AgriMine</span></div>'
            '<div class="brand-tag">Smarter crops. Healthier farms.</div></div>',
            unsafe_allow_html=True,
        )
    draw_nav()
    # The assessment card is drawn into a slot so a page can refresh it later in the
    # same run (the Crop Advisor does, after it has made its prediction).
    with st.sidebar.container(key="am_side_assess"):
        st.session_state[_SIDE_SLOT_KEY] = st.empty()
    draw_tagline()
    refresh_sidebar()


def refresh_sidebar() -> None:
    """(Re)draw the read-only "Current assessment" card in the sidebar."""
    from utils.i18n import crop_name   # the sidebar follows the language too
    from utils.session import SOIL_PAGE, get_assessment_record   # local import: no cycle at load time

    slot = st.session_state.get(_SIDE_SLOT_KEY)
    if slot is None:
        return
    record = get_assessment_record()
    with slot.container():
        if record is None:
            st.markdown('<div class="side-card"><div class="side-label">Current assessment</div>'
                        '<div class="side-empty">None yet. Start with your soil and weather values.</div></div>',
                        unsafe_allow_html=True)
            try:
                st.page_link(SOIL_PAGE, label="New assessment", icon=":material/add:")
            except Exception:   # page opened on its own (e.g. in tests): no navigation to link to
                pass
            return
        v = record["values"]
        ident = f"#{record['id']}" if record.get("id") is not None else "unsaved"
        crop = record.get("predicted_crop")
        crop_html = (f'<div class="side-crop">{crop_emoji(crop)} {_esc(crop_name(crop))}</div>' if crop
                     else '<div class="side-empty">Open the Crop Advisor for a prediction.</div>')
        st.markdown(
            f'<div class="side-card"><div class="side-label"><span>Current assessment</span>'
            f'<span>{_esc(ident)}</span></div>{crop_html}'
            f'<div class="side-values">N {v["N"]:g} · P {v["P"]:g} · K {v["K"]:g}<br>'
            f'pH {v["ph"]:g} · {v["temperature"]:g} °C · {v["rainfall"]:g} mm</div></div>',
            unsafe_allow_html=True,
        )


# =============================================================================
# 6. page_header()
# =============================================================================
def page_header(title: str, caption: str, eyebrow: str | None = None, accent: str | None = None,
                crumbs: list[str] | None = None) -> None:
    """
    Breadcrumb, eyebrow (technique), title, one-line subtitle and an accent underline.
    accent  - the page's colour (e.g. ALGO["id3"]); it also colours the decision-path
              timeline, rule cards and level meters further down the page.
    crumbs  - breadcrumb parts; the default is ["Home", title].
    """
    accent = accent or FOREST
    crumbs = crumbs or ["Home", title]
    # The accent becomes a page-wide CSS variable so every helper below can use it.
    st.markdown(f"<style>:root {{ --accent: {accent}; }}</style>", unsafe_allow_html=True)
    crumbs_html = "".join(f"<span>{_esc(c)}</span>" for c in crumbs)
    eyebrow_html = f'<div class="am-eyebrow">{_esc(eyebrow)}</div>' if eyebrow else ""
    st.markdown(
        f'<div class="am-header"><nav class="am-crumbs" aria-label="Breadcrumb">{crumbs_html}</nav>'
        f'{eyebrow_html}<div class="am-title" role="heading" aria-level="1">{_esc(title)}</div>'
        f'<div class="am-subtitle">{_esc(caption)}</div></div>',
        unsafe_allow_html=True,
    )


def section_note(text: str) -> None:
    """A short muted line directly under a subheader."""
    st.markdown(f'<div class="am-section-note">{_esc(text)}</div>', unsafe_allow_html=True)


# =============================================================================
# 7. style_fig()  (Plotly charts)
# =============================================================================
def _same_scale(a, b) -> bool:
    """True when two Plotly colour scales are identical (used to spot the default one)."""
    try:
        return tuple((float(p), str(c)) for p, c in a) == tuple((float(p), str(c)) for p, c in b)
    except Exception:
        return False


def style_fig(fig, height: int = 360):
    """Apply the shared look to a Plotly figure and return it: neon on a transparent background."""
    has_title = bool(getattr(fig.layout.title, "text", None))
    fig.update_layout(
        height=height,
        font=dict(family=FONT_STACK, color=INK, size=13),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=8, r=8, t=44 if has_title else 16, b=8),
        colorway=PALETTE,
        title=dict(font=dict(family=HEADING_STACK, size=16, color=INK), x=0.0, xanchor="left"),
        legend=dict(title_text="", font=dict(size=12, color=INK_2), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor=SIDEBAR, bordercolor=LINE, font=dict(family=FONT_STACK, size=13, color=INK)),
        modebar=dict(bgcolor="rgba(0,0,0,0)", color=INK_3, activecolor=FOREST_DEEP),
        colorscale=dict(sequential=SEQ_SCALE, sequentialminus=SEQ_SCALE),
        bargap=0.28,
    )
    # automargin is set explicitly: Streamlit does not keep the template's value, and
    # without it long tick labels are cut off at the edge of the chart.
    axis = dict(automargin=True, gridcolor=GRID, linecolor=LINE, zeroline=False, showline=False,
                tickfont=dict(size=12, color=INK_2), title_font=dict(size=12, color=INK_2))
    fig.update_xaxes(**axis)
    fig.update_yaxes(**axis)

    # Plotly Express colour bars default to purple/yellow: swap that default for our
    # sequential scale, but keep any scale a page chose on purpose.
    try:
        default = fig.layout.template.layout.colorscale.sequential
        for ax in fig.select_coloraxes():
            if ax.colorscale is None or _same_scale(ax.colorscale, default):
                ax.colorscale = SEQ_SCALE
            if ax.colorbar is not None:
                ax.colorbar.update(outlinewidth=0, tickfont=dict(size=11, color=INK_2))
    except Exception:
        pass

    # Rounded bar corners (needs a recent Plotly; older versions simply skip this).
    try:
        fig.update_traces(marker_cornerradius=6, selector=dict(type="bar"))
    except Exception:
        pass
    return fig


def gradient_fill(color: str, top: float = 0.45) -> dict:
    """
    Keyword arguments for a go.Scatter area that fades from the line colour to transparent:
        go.Scatter(x=..., y=..., fill="tozeroy", **gradient_fill(ALGO["kmeans"]))
    """
    return dict(line=dict(color=color, width=2.5), fillcolor=rgba(color, top / 2),
                fillgradient=dict(type="vertical", colorscale=[[0, rgba(color, 0.0)], [1, rgba(color, top)]]))


# =============================================================================
# 8. show_chart() / show_table()
# =============================================================================
# Chart toolbar: keep download, zoom, pan and reset; drop the rest.
_CHART_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToRemove": ["select2d", "lasso2d", "zoomIn2d", "zoomOut2d", "autoScale2d",
                               "toggleSpikelines", "hoverClosestCartesian", "hoverCompareCartesian"],
}


def show_chart(fig, key: str | None = None, stretch: bool = False) -> None:
    """
    Draw a Plotly chart at full width inside a card (theme=None keeps our colours).
    Give every chart on a page its own key: Streamlit refuses two identical charts
    without keys in the same run. stretch=True fills the height of its container (the Home cards
    set that height in CSS, scaled to the window).
    """
    extra = {"key": key} if key else {}
    if stretch:
        extra["height"] = "stretch"
    with st.container(key=f"am_chart_{key}" if key else None):
        try:
            st.plotly_chart(fig, theme=None, width="stretch", config=_CHART_CONFIG, **extra)
        except TypeError:  # older Streamlit without the width / height arguments
            extra.pop("height", None)
            st.plotly_chart(fig, theme=None, use_container_width=True, **extra)


def status_cell(ok: bool) -> str:
    """CSS for a table cell (pandas Styler): green when ok, amber when not."""
    return ("background-color: rgba(46, 158, 106, 0.14); color: #1F6B42" if ok
            else "background-color: rgba(227, 169, 43, 0.14); color: #FDE68A")


def show_table(df, **kwargs) -> None:
    """Draw a (sortable) table at full width, hiding the index by default."""
    kwargs.setdefault("hide_index", True)
    try:
        st.dataframe(df, width="stretch", **kwargs)
    except TypeError:  # older Streamlit without the width argument
        st.dataframe(df, use_container_width=True, **kwargs)


# =============================================================================
# 9. Reusable HTML helpers
# =============================================================================
# Each helper returns an HTML string built on the CSS above. Show it with
#     render_html(kpi_card("Records", "2,200"))
# Because they return strings you can also put them inside columns. All text is
# escaped, so data or user input cannot break the layout.

def render_html(html: str) -> None:
    """Shortcut: draw one of the helper strings below."""
    st.markdown(html, unsafe_allow_html=True)


def kpi_card(label: str, value, hint: str = "") -> str:
    """Number tile on a navy card: small label, big value, optional hint underneath."""
    hint_html = f'<div class="kpi-hint">{_esc(hint)}</div>' if hint else ""
    return (f'<div class="kpi"><div class="am-label">{_esc(label)}</div>'
            f'<div class="kpi-value">{_esc(value)}</div>{hint_html}</div>')


def sparkline_svg(values, color: str = "#FFFFFF", width: int = 240, height: int = 38) -> str:
    """
    A tiny line chart as inline SVG: the values are scaled to fill the box, drawn as a
    line with a soft fade underneath. Needs at least two values (otherwise a flat line).
    """
    vals = [float(v) for v in values if v == v] or [0.0, 0.0]   # v == v drops NaN
    if len(vals) == 1:
        vals = vals * 2
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    pad = 3
    pts = [(i * width / (len(vals) - 1), pad + (height - 2 * pad) * (1 - (v - lo) / span)) for i, v in enumerate(vals)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"0,{height} {line} {width},{height}"
    gid = f"sp{abs(hash((tuple(vals), color))) % 10**8}"
    return (f'<svg class="kpi-spark" viewBox="0 0 {width} {height}" preserveAspectRatio="none" aria-hidden="true">'
            f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{color}" stop-opacity="0.35"/>'
            f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></linearGradient></defs>'
            f'<polygon points="{area}" fill="url(#{gid})"/>'
            f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="2" '
            f'stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/></svg>')


def kpi_tile(label: str, value, note: str, color: str, series) -> str:
    """Solid vivid KPI tile: label, big white value, one-line note and a white sparkline of `series`."""
    return (f'<div class="kpi-solid" style="background: linear-gradient(135deg, {color} 0%, {color} 55%, '
            f'{rgba(color, 0.82)} 100%)"><div class="kpi-label">{_esc(label)}</div>'
            f'<div class="kpi-big">{_esc(value)}</div><div class="kpi-note">{_esc(note)}</div>'
            f'{sparkline_svg(series)}</div>')


def info_card(title: str, body: str) -> str:
    """Navy box with a bold title and a short explanation."""
    return (f'<div class="info-card"><div class="info-card-title">{_esc(title)}</div>'
            f'<div class="info-card-body">{_esc(body)}</div></div>')


_BADGE_LEVELS = {"neutral", "success", "info", "warning", "danger", "accent"}


def badge(text: str, level: str = "neutral") -> str:
    """Small coloured pill. level: neutral, success, info, warning, danger or accent (amber)."""
    level = level if level in _BADGE_LEVELS else "neutral"
    return f'<span class="badge badge-{level}">{_esc(text)}</span>'


def chip(text: str, key: str | None = None, crop: bool = False) -> str:
    """Rounded tag, optionally 'key · text' (e.g. Humidity · medium). crop=True gives the green crop style."""
    key_html = f"<b>{_esc(key)}</b>" if key else ""
    return f'<span class="chip{" chip-crop" if crop else ""}">{key_html}{_esc(text)}</span>'


def score_bar(label: str, pct, accent: bool = False, suffix: str = "%", color: str | None = None) -> str:
    """
    Label and value above a thin bar. pct is 0 to 100 (values outside are clamped).
    accent=True draws it amber; color='#F472B6' draws it in any colour (e.g. an algorithm's).
    """
    try:
        p = float(pct)
        p = 0.0 if p != p else max(0.0, min(100.0, p))   # p != p is True only for NaN
    except (TypeError, ValueError):
        p = 0.0
    shown = f"{p:.1f}".rstrip("0").rstrip(".")
    fill_style = f"width:{p:.1f}%" + (f";background:linear-gradient(90deg,{rgba(color, 0.55)},{color})" if color else "")
    return (f'<div class="score" role="progressbar" aria-valuemin="0" aria-valuemax="100" '
            f'aria-valuenow="{shown}" aria-label="{_esc(label)}"><div class="score-head">'
            f'<span class="score-label">{_esc(label)}</span><span class="score-pct">{shown}{_esc(suffix)}</span></div>'
            f'<div class="score-track"><div class="score-fill{" clay" if accent else ""}" '
            f'style="{fill_style}"></div></div></div>')


def result_card(label: str, value, sublabel: str = "", emoji: str = "", body_html: str = "") -> str:
    """The main answer, e.g. result_card("ID3 recommends", "Rice", emoji="🌾"). body_html is trusted HTML."""
    emoji_html = f'<div class="result-emoji" aria-hidden="true">{_esc(emoji)}</div>' if emoji else ""
    sub_html = f'<div class="result-sub">{_esc(sublabel)}</div>' if sublabel else ""
    body = f'<div class="result-body">{body_html}</div>' if body_html else ""
    return (f'<div class="result-card"><div class="result-top">{emoji_html}<div>'
            f'<div class="am-label">{_esc(label)}</div><div class="result-value">{_esc(value)}</div>'
            f'</div></div>{sub_html}{body}</div>')


def outcome_card(title: str, crop: str, rows: list[tuple[str, str]], highlight: bool = False) -> str:
    """One side of a comparison: title, crop name with emoji, then label/value rows."""
    rows_html = "".join(f'<div class="outcome-row"><span>{_esc(k)}</span><b>{_esc(v)}</b></div>' for k, v in rows)
    return (f'<div class="outcome{" outcome-hit" if highlight else ""}"><div class="am-label">{_esc(title)}</div>'
            f'<div class="outcome-crop"><span aria-hidden="true">{crop_emoji(crop)}</span>{_esc(crop_title(crop))}</div>'
            f'{rows_html}</div>')


def crop_card(label: str, crop: str, body_html: str = "") -> str:
    """Small card: label, crop name with emoji, then trusted body HTML (e.g. a score_bar)."""
    return (f'<div class="am-card"><div class="am-label">{_esc(label)}</div>'
            f'<div class="outcome-crop"><span aria-hidden="true">{crop_emoji(crop)}</span>'
            f'{_esc(crop_title(crop))}</div>{body_html}</div>')


def step_flow(steps: list[str]) -> str:
    """Horizontal path of chips joined by arrows: step 1 -> step 2 -> step 3."""
    parts = []
    for i, step in enumerate(steps):
        if i:
            parts.append('<span class="step-arrow">&rarr;</span>')
        parts.append(f'<span class="step-chip"><b>{i + 1}</b>{_esc(step)}</span>')
    return f'<div class="step-flow">{"".join(parts)}</div>'


_LEVELS = ["low", "medium", "high"]


def level_meter(level: str) -> str:
    """Three segments (low / medium / high) with the matching one filled."""
    segs = "".join(f'<span class="{"on" if lv == level else ""}"></span>' for lv in _LEVELS)
    legend = "".join(f'<span class="{"on" if lv == level else ""}">{lv}</span>' for lv in _LEVELS)
    return f'<div class="meter" aria-label="Level: {_esc(level)}">{segs}</div><div class="meter-legend">{legend}</div>'


def feature_tile(label: str, value: str, unit: str, level: str, tooltip: str = "", extra_html: str = "") -> str:
    """Soil Analysis tile: label, value + unit, low/medium/high meter. extra_html is trusted HTML (e.g. a badge)."""
    unit_html = f"<small>{_esc(unit)}</small>" if unit else ""
    return (f'<div class="tile" title="{_esc(tooltip)}"><div class="tile-head"><span class="am-label">{_esc(label)}</span>'
            f'{extra_html}</div><div class="tile-value">{_esc(value)}{unit_html}</div>{level_meter(level)}</div>')


def timeline(steps: list[dict], final: str) -> str:
    """
    Vertical decision path. Each step: {feature, value, level, range, gain, rows}.
    The info-gain bar is relative to the largest gain on the path. final = text of the last node.
    """
    top = max((s["gain"] for s in steps), default=0) or 1
    items = []
    for i, s in enumerate(steps, start=1):
        pct = 100 * s["gain"] / top
        items.append(
            f'<li class="tl-step"><div class="tl-dot">{i}</div><div class="tl-body">'
            f'<div class="tl-title">{_esc(s["feature"])} {chip(s["level"])}</div>'
            f'<div class="tl-meta">Your value <b>{_esc(s["value"])}</b> falls in {_esc(s["range"])} · '
            f'{_esc(s["rows"])} training rows here</div>'
            f'<div class="tl-gain"><span>Information gain</span><div class="score-track">'
            f'<div class="score-fill" style="width:{pct:.0f}%"></div></div><b>{s["gain"]:.3f}</b></div>'
            f'</div></li>'
        )
    items.append(f'<li class="tl-step"><div class="tl-dot">&#10003;</div><div class="tl-body">'
                 f'<div class="tl-title">{_esc(final)}</div></div></li>')
    return f'<ol class="timeline tl-end-wrap">{"".join(items[:-1])}</ol><ol class="timeline tl-end">{items[-1]}</ol>'


def _item_chip(item: str) -> str:
    """'humidity=medium' -> chip 'Humidity · medium'; 'crop=rice' -> green crop chip 'Rice'."""
    name, _, val = item.partition("=")
    if name == "crop":
        return chip(f"{crop_emoji(val)} {crop_title(val)}", crop=True)
    pretty = FEATURE_NAME.get(name, name.capitalize())
    return chip(val, key=f"{pretty} · ")


def rule_card(rank: int, antecedent: str, consequent: str, confidence: float, lift: float, support: float) -> str:
    """Apriori rule as IF [chips] THEN [chip], with confidence / lift / support along the bottom."""
    left = "".join(_item_chip(x) for x in antecedent.split(" AND "))
    right = "".join(_item_chip(x) for x in consequent.split(" AND "))

    def stat(label, value, cls=""):
        return f'<div class="rule-stat"><span>{label}</span><b class="{cls}">{value}</b></div>'

    return (f'<div class="rule"><div class="rule-rank">Rule {rank}</div>'
            f'<div class="rule-row"><span class="rule-kw">IF</span><div class="rule-chips">{left}</div></div>'
            f'<div class="rule-row"><span class="rule-kw">THEN</span><div class="rule-chips">{right}</div></div>'
            f'<div class="rule-spacer"></div>'
            f'<div class="rule-stats">{stat("Confidence", f"{confidence:.0%}")}'
            f'{stat("Lift", f"{lift:.1f}", "lift")}{stat("Support", f"{support:.1%}")}</div></div>')


def card_grid(cards: list[str], cols: int = 3) -> str:
    """Put card HTML strings in one equal-height row (stacks on small screens)."""
    return f'<div class="card-grid" style="--cols:{int(cols)}">{"".join(cards)}</div>'


def star_schema(fact: tuple[str, int], dims: list[tuple[str, int]]) -> str:
    """Fact table in the centre, up to four dimension tables around it (name, row count)."""
    def wrap(name):   # allow line breaks only after underscores
        return _esc(name).replace("_", "_<wbr>")

    def node(name, rows, cls):
        return (f'<div class="schema-node {cls}"><code>{wrap(name)}</code>'
                f'<div class="schema-rows">{rows:,} rows</div></div>')
    places = ["schema-n", "schema-w", "schema-e", "schema-s"]
    dims_html = "".join(node(n, r, places[i]) for i, (n, r) in enumerate(dims[:4]))
    fact_html = (f'<div class="schema-node schema-fact"><div class="am-label">Fact</div><code>{wrap(fact[0])}</code>'
                 f'<div class="schema-rows">{fact[1]:,} rows</div></div>')
    return f'<div class="schema"><div class="schema-lines"></div>{dims_html}{fact_html}</div>'


def zone_flow(zones: list[tuple[str, str, str]]) -> str:
    """Three boxes joined by arrows, e.g. raw -> curated -> warehouse. zones = [(name, body, colour)]."""
    parts = []
    for i, (name, body, color) in enumerate(zones):
        if i:
            parts.append('<div class="zone-arrow" aria-hidden="true">&rarr;</div>')
        parts.append(f'<div class="zone" style="--zone:{color}"><div class="zone-name">{_esc(name)}</div>'
                     f'<div class="zone-body">{_esc(body)}</div></div>')
    return f'<div class="zone-flow">{"".join(parts)}</div>'


# =============================================================================
# 10. dash_card()  (Dashboard cards)
# =============================================================================
@contextmanager
def dash_card(key: str, title: str, subtitle: str, accent: str, page: str | None = None,
              tag: str = "", link_label: str = "Open full page"):
    """
    One dashboard card: coloured top edge, title, one-line subtitle, then whatever the
    `with` block draws, then a link to the full page.
        with dash_card("id3", "Information gain", "Root split of the tree", ALGO["id3"], "pages/3_Crop_Advisor.py"):
            show_chart(fig, key="dash_id3")
    """
    with st.container(key=f"am_dash_{key}"):
        tag_html = f'<span class="dash-tag">{_esc(tag)}</span>' if tag else ""
        st.markdown(
            f"<style>.st-key-am_dash_{key} {{ --accent: {accent}; }}</style>"
            f'<div class="dash-head"><div><div class="dash-title">{_esc(title)}</div>'
            f'<div class="dash-sub" title="{_esc(subtitle)}">{_esc(subtitle)}</div></div>{tag_html}</div>',
            unsafe_allow_html=True,
        )
        yield
        if page:
            try:
                st.page_link(page, label=link_label, icon=":material/arrow_forward:")
            except Exception:   # page opened on its own (e.g. in tests): no navigation to link to
                pass

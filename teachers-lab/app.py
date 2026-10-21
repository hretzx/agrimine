"""
teachers-lab/app.py
-------------------
The technical lab (Streamlit). Run from this folder:  streamlit run app.py     (or: make lab)
It uses the same core/ package as the web app and the API (core/ lives one folder up, so that is put on the import path first).
 - sets the page config
 - builds the navigation from the files in the pages/ folder. The landing page is "For teachers": it links to every
   technical page. The farmer pages (Home, What should I grow?, Crop Doctor, Plan B) live in the web app only.
The sidebar shows one link, For teachers; the technical pages are reached from that page.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))      # so "import core" works from this folder

import streamlit as st

from utils.farm_ui import register_pages
from utils.style import page_number, page_slug, page_title

st.set_page_config(page_title="AgriMine lab", page_icon=":material/eco:", layout="wide")
ROOT = Path(__file__).parent
LANDING = "17_For_Teachers"      # the page the lab opens on

# Every page file is registered (so links between pages work); the sidebar shows only the landing page: see utils/farm_ui.
registry, pages = {}, []
for f in sorted((ROOT / "pages").glob("*.py"), key=lambda p: (page_number(p.stem), p.stem)):
    if f.stem == LANDING:
        page = st.Page(f"pages/{f.name}", title=page_title(f.stem), default=True)
        registry["nav_teachers"] = page
    else:
        page = st.Page(f"pages/{f.name}", title=page_title(f.stem), url_path=page_slug(f.stem))
    pages.append(page)
register_pages(registry)
st.navigation(pages, position="hidden").run()

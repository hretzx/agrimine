# AgriMine changelog

## Deployment fix: CORS for the Vercel web app, and a way to see what Render runs
Reported: the web app on Vercel could not call the API on Render ("No Access-Control-Allow-Origin header" on the preflight). The CORS middleware in the repo is right (a test now sends the preflight for `/api/meta`, `/api/checks?limit=1` and `/api/checks?limit=4`), so the running service was not this code or did not answer at all. Changes: CORS origins are settable with `AGRIMINE_CORS_ORIGINS` and `AGRIMINE_CORS_ORIGIN_REGEX`; an unhandled crash is now a JSON 500 that still carries the CORS headers (before, the browser showed a CORS error instead of the real error); `python -m api` listens on `0.0.0.0:$PORT` when `PORT` is set; the lab is off by default on Render; `/api/health` reports the running commit on Render; `render.yaml`; `tools/check_cors.py` tests a deployed API the way a browser does. Tests: 24 API tests (7 new).

## Phase 8: cut-over
The technical lab no longer has its own Home, What should I grow?, Crop Doctor or Plan B (they are in the web app only). It opens on its For teachers page, which lists every technical page, and its sidebar has that one link. `make release` builds the site and packs `dist/agrimine-release.zip` (the committed files plus the prebuilt `web/out`: Python only to run, no Node). README and DEMO_SCRIPT rewritten for the web app. Tests: lab smoke tests updated (14), a real-browser lab test for the new front door, `tests/test_release.py`. Clean-machine run from the zip (new folder, new virtualenv, `pip install -r requirements.txt`, `python -m api`, no Node on the PATH): everything came up, the lab started and stopped with the API, Home showed the same numbers as the development build.

## Phase 7d (5 of 5): Hierarchical page, the five headline pages are done
New page `/en|mr/teachers/hierarchical/` and API route `GET /api/teachers/hierarchical?method=&k=` (logic in `core/teachers.py::hierarchical_report`). It is the lab's Hierarchical page: a choice of linkage (Ward, Average, Complete, Single) and a slider for k; the cophenetic correlation and last merge height; the dendrogram of the 22 crops with the cut line and cluster colours; the k clusters; and the top-down DIANA splits, with whether DIANA and the chosen linkage agree. Phone layout, English and Marathi. ID3, Naive Bayes, K-Means, Apriori and Hierarchical are now all in the web app. Still only in the lab: FP-Growth and Eclat, Water Lab, What-if Lab, Data Insights, Data Lake, Data Prep. Tests: 55 unit, 206 browser, 80 Python.

## Phase 7d (4 of 5): Apriori page
New page `/en|mr/teachers/apriori/` and API route `GET /api/teachers/apriori` (logic in `core/teachers.py::apriori_report`). It is the lab's Pattern Mining: sliders for minimum support and confidence, the largest pattern size, a crop filter and a "rules that end in a crop" switch; the number of frequent itemsets, rules and the measured mining time; the three strongest rules; a sortable table of the strongest hundred; the top ten by lift; and what support, confidence and lift mean. At the defaults it gives the same 821 rules as Home's "Patterns found" (a test compares them). Phone layout, English and Marathi. Tests: 55 unit, 198 browser, 79 Python.

## Phase 7d (3 of 5): K-Means page
New page `/en|mr/teachers/kmeans/` and API route `POST /api/teachers/kmeans?k=` (logic in `core/teachers.py::kmeans_report`). It is the lab's Cluster Explorer: a slider for k (2 to 10), inertia, silhouette and how much the 2D map keeps; which group your readings fall in; every record on the PCA map; each group's average readings in real units and its most common crop; a crops-by-group table; and the elbow and silhouette charts with your k marked. Same numbers as Home's "Farms like yours" (a test compares them). Editable readings, phone layout, English and Marathi. The group palette now has ten colours. Tests: 55 unit, 190 browser, 78 Python.

## Phase 7d (2 of 5): Naive Bayes page
New page `/en|mr/teachers/naive-bayes/` and API route `POST /api/teachers/naive-bayes` (logic in `core/teachers.py::nb_report`). It is the lab's Model Council: ID3 and Gaussian Naive Bayes on the same readings, whether they agree, the six most likely crops, which readings pushed Naive Bayes (the bars add up to the log of the odds), Bayes' formula worked out with your numbers, and per-crop accuracy for both. Editable readings, phone layout, English and Marathi. Found and fixed on the way: the shared progress bar passed tiny values such as 1.8e-8 to `aria-valuenow` in exponent form, which is invalid (it affected every bar). Tests: 55 unit, 187 browser (run one project at a time), 77 Python.

## Mobile support for the whole UI
Update: the phone navigation is one row of tabs that scrolls sideways and opens on the current page.
Every page now works on a phone (tested at 390x844 and 360x640, English and Marathi, light and dark). Below 768px the sidebar is a header with the five links and a "Current check / Recent checks" toggle; page grids stack into one column (two for the readings); the Crop Doctor rows, the checks list, the ranking and the Teachers list re-flow; the comparison table scrolls inside its own keyboard-reachable box; buttons and links are at least 34px to tap; number inputs are 16px so phones do not zoom in. Desktop is unchanged (all earlier baselines still match). New: `e2e/mobile.spec.ts` (14 tests incl. 8 phone baselines), axe on every page at phone width, and the sidebar walk now also asserts no sideways scrolling at every size. Tests: 55 unit, 172 browser, 76 Python.

## Fix: the sidebar on narrow windows (and a test that walks every page and size)
Below 768px wide the sidebar was still a 268px column, leaving about 120px for the page on a phone. It is now a header across the top (brand and the five links, which scroll sideways if needed). New test: every page x English/Marathi x 8 window sizes (1920 down to 390 wide) x scrolled to top, middle and bottom, checking the sidebar's position, size, picture space and that every link can be reached. It fails on the old sidebar. Still open: on a phone a few pages (Crop Doctor most) are wider than the screen; that is page content, not the sidebar.

## Phase 7 (part): first teacher page ported, ID3 decision tree
New page `/en|mr/teachers/id3/` and API route `POST /api/teachers/id3` (logic in `core/teachers.py`). It shows what the lab's Crop Advisor shows, in the new design, in English and Marathi: ID3's crop, how pure the final node was, held-out accuracy, every question the tree asked with its information gain, alternatives by profile match, bins, depth and the crops the tree finds hardest. The readings can be edited to try values (nothing is saved). For teachers links to it. Tests: 55 unit, 134 browser, 76 Python. Next: Naive Bayes, K-Means, Apriori, Hierarchical.

## Phase 7 (part): the technical lab moved, connected, and started by the API
The Streamlit app now lives in `teachers-lab/` (run: `make lab`). It reads the same saved checks as the web app: `?check=N` in the address, else the one chosen earlier in the session, else the newest check. The web's For teachers page links each algorithm to its lab page on the current check. Tests: 55 unit, 122 browser (5 of them drive a real lab), 73 Python. `python -m api` now starts the lab too (and stops it); `GET /api/lab` reports whether it is up; the links show only then, and the first link no longer shows Streamlit's "Page not found" dialog (the lab is warmed up first). `AGRIMINE_LAB=0` turns it off.

## Phase 6 (part): all 22 crop drawings, accessibility pass
`web/`: the 14 missing crop drawings (every crop now has one; tests fail if one is missing or two look alike). axe-core accessibility tests on every page, light and dark, English and Marathi (28 pages) plus keyboard tests (visible focus on every control, new "skip to the page content" link). They found low contrast in light mode: five colour tokens darkened slightly, nothing else changed visibly. Still to do for Phase 6: the farmers' review of the Marathi wording and of the drawings. Tests: 52 unit, 114 browser, 60 Python.

## Fixes: old checks and the Home chips
Checks saved by the first release had an old prediction ("cotton") and no probability, so the list and sidebar disagreed with Home. The startup backfill now redoes any check with no probability using the current model (it stamps `model_version`); the five checks in the real database were redone (a copy of the database before this is `data/agrimine.db.bak-before-backfill`). The three reading chips in the Home hero no longer cut off labels such as "Temperature" (8 new browser tests: English and Marathi at four widths). 58 Python tests, 70 browser tests.

## Sidebar fixes (web)
Landscape has its own space under the scrolling content (no overlap at short windows, edge fades), dead search and chevron controls removed, "View all checks" opens a real list at `/checks/`, recent checks keep the current page. 16 sidebar browser tests (sizes 1920x1080 to 1366x500, keyboard scroll, links), 62 browser tests in total; the other baselines changed in the sidebar column only (checked pixel by pixel).

## Phase 5 of the architecture plan: the farmer pages
`web/`: What should I grow?, Crop Doctor, Plan B, For teachers (first version). Shared readings editor (edit values to try them; nothing is saved), compare tables, Base UI select. Sidebar Crop Doctor chip defined (soil health of the recommended crop) and wired; every nav row has one fixed height. API: `/meta` carries `default` (dataset median) per reading, `/doctor` readings carry `tip_key`; the 14 doctor tips are translated in the web app (Marathi draft). Tests: 52 unit, 46 browser (isolated server and database per group), 57 Python. Fixes to the test harness are listed in docs/ARCHITECTURE_PLAN.md.

## Phase 4 of the architecture plan: Home on real data
**Fix:** the web sidebar now stays in place while the page scrolls (it was scrolling away); two new browser tests scroll and check it (25 browser tests in total).
`web/` Home and the New soil check form, all from the API. API: `/insights/patterns` now returns `{total, items}`, `/insights/accuracy` returns `seed` (a number), `/meta` returns crop families with Marathi names; the split seed is a named constant (`core.models.SPLIT_SEED`). Tests: 47 unit, 23 browser (visual tolerance tightened from 0.3% to 40 pixels after a changed sentence slipped through), 57 Python.

## Phase 3 of the architecture plan: the web scaffold
New `web/` (Next.js 16 static export, React 19, Tailwind 4, Base UI, Lucide, Plus Jakarta Sans + Noto Sans Devanagari): tokens with light and dark, a component library, generated API types, i18n (English, Marathi), a component gallery, 20 unit tests, 11 browser tests with visual baselines. Root `Makefile` (`make api | dev | build | contract | test`). `AGRIMINE_DEV=1` enables CORS for the Next dev server. The OpenAPI contract now declares the error shape (`ErrorBody`).

## Phase 2 of the architecture plan: the API
New `api/` package (FastAPI): 12 routes, pydantic schemas, one error shape, `api/openapi.json` as the contract (drift test). New `core/checks.py`: a soil check is validated, predicted and saved in ONE transaction; the `assessments` table gains `probability`, `id3_crop`, `model_version` (older databases are migrated and unpredicted rows are backfilled at start-up). `core/cache.py` is now thread-safe. `AGRIMINE_DB` selects the database file. 10 API tests; real-server timings: start-up 2.4 s, endpoints 2-7 ms.

## Phase 0 and 1 of the architecture plan (docs/ARCHITECTURE_PLAN.md)
**Behaviour changes (Phase 0).** Top 3 is ordered by Naive Bayes probability and shows the profile similarity (0-100) as a separate bar; Plan B alternatives come from similarity. Marathi mode shows Marathi farmer crop names (draft, farmers review). N, P and K are shown without "kg/ha" until the source unit is confirmed.
**Refactor (Phase 1, no behaviour change).** `algorithms/`, `db/`, `utils/preprocessing|models|advice|lake` moved into a Streamlit-free `core/` package; new `core/cache.py`, `core/features.py`, `core/crops.py`; the 9 duplicated feature-label dictionaries and the crop tables now read from the two registries. 46 tests (was 33); the Home screenshot before and after differs by 3 pixels of 1,572,864.

## Sage Field redesign (farmer-first)
**Look.** The dark Navy Harvest theme is replaced by a light "Sage Field" theme built from measurements of the reference design
(1536 x 1024): sage sidebar `#EBF4E9`, page `#F5F6F4`, white cards with a hairline border and soft shadow, pastel summary cards
`#EDF6EC / #F9F3E2 / #FCECE6`, near-black navy text `#061326` with `#556D84` subtitles, green / yellow / coral status colours
(`#2FB573 / #FFC72D / #FF6971` bars). Card positions match the reference within 1 to 3 px at 1536 x 1024 (`DESIGN_MEASUREMENTS.md` has the numbers).
The Home layout is sized in "design pixels" scaled to the window (`--u` in `utils/farm_ui.py`), so it keeps its proportions and fits one screen
at 1536 x 1024 and 1440 x 900; at 1366 x 768 it scrolls by about 40 px because text is not allowed to shrink below 80%.

**Navigation.** Five sidebar items: Home, What should I grow?, Crop Doctor, Plan B, For teachers. All 12 earlier pages are kept and
reachable from For teachers (the sidebar is custom, `position="hidden"` in `st.navigation`).

**Home** (the main product): summary cards, best-crop hero, Top 3, Crop Doctor, Plan B, Farms like yours (K-Means), What each crop needs (climate bubbles),
crop requirements rings, What matters most (ID3 information gain), Patterns found (Apriori); then a technical-insights strip (Naive Bayes, dendrogram,
itemset miners, accuracy) and recent assessments. Every value is computed from the data or the models. Shown, but not in the dataset and therefore **not built**:
the reference's farm size, soil type, seasonal-suitability curve, planting window and month-on-month percentages.

**New pages:** What should I grow? (ranking, reasons, comparison), Crop Doctor (readings vs ranges, tips), Plan B (alternatives and what they need),
For teachers (algorithm map, evaluation, timings). **Language:** working English / Marathi toggle (`utils/i18n.py`).

**Fixes.** Recent assessments no longer show "None": a saved check says "Saved, not predicted yet" / "Pending" until a prediction has run, then "Predicted"
with the crop (the prediction runs when Home, What should I grow? or the Crop Advisor opens with that check).

**Deliberate deviations from the pixel-measured colours** (accessibility): status *text* uses a darker shade of the bar colour (for example Good `#178A4C`
instead of `#22A75D`) so it passes WCAG AA; the primary button is `#058A5A`.

**Tests.** `tests/test_core.py`: match scores, recommendation vs Naive Bayes, soil-health thresholds against the crop's percentiles, overall health, clusters,
translations (20 checks). `tests/smoke_test.py`: all 17 pages, the six Home cards, the Marathi toggle, "Pending" in recent assessments, Crop Doctor tips, Plan B (13 checks).

---

## Navy Harvest upgrade (replaced by Sage Field above)
## Navy Harvest upgrade
**Theme.** The light "Field Journal" theme is replaced by a dark navy one (`.streamlit/config.toml`, `utils/style.py`). Old token names still work (their values changed). Sidebar groups Dashboard / Assess / Mine / Data with a coloured dot per page; pages sort by their number, so `10_` comes after `9_`. Each algorithm has its own accent colour.

**Dashboard.** Rebuilt as an analytics dashboard: four solid KPI cards with sparklines, K-Means cluster map (k = 3 / 4 / 5, your assessment as an X), model accuracy donut and bars, ID3 information gain, Naive Bayes posterior, regression fit, crop dendrogram, Apriori rule bubbles and the miners' run times, then the recent assessments table. The climate map and nutrient heatmap stay in tabs below. All models are cached. The old "How it works" strip and the intro banner were removed to make room.

**New algorithms** (`algorithms/`, NumPy only): `naive_bayes.py`, `regression.py`, `hierarchical.py` (4 linkages, `cut_tree`, cophenetic correlation, DIANA), `fpgrowth.py` (FP-Growth, Eclat, closed and maximal itemsets). The 80/20 stratified split (seed 42) now lives in one helper, `stratified_split()` in `utils/models.py`, shared by ID3 and Naive Bayes; ID3's held-out accuracy is unchanged at 90.2%.

**New pages:** Model Council, Water Lab, Hierarchical, FP-Growth and Eclat, Data Lake, Data Prep. Each has a short "How it works" expander. `run_etl()` takes an optional dataframe, so the Data Lake loads the warehouse from its curated file; `utils/lake.py` holds the lake file code.

**Tests.** `tests/test_core.py` gained checks for Naive Bayes, regression against `np.polyfit`, hierarchical heights against scipy (optional, skipped without it), `cut_tree`, DIANA, Apriori = FP-Growth = Eclat on the real data, closed / maximal itemsets against brute force, the data-prep helpers and the data lake pipeline. `tests/smoke_test.py` opens all 13 pages with `AppTest` and also drives their controls (every dashboard k, every linkage, every regression target, the lake button).

**Measured on the real 2,200-row data** (80/20 split, seed 42): ID3 held-out accuracy 90.2%; Naive Bayes 99.5%; best simple regression (P and K) held-out R-squared 0.60; silhouette 0.252 (k = 4), 0.252 (k = 3), 0.292 (k = 5), highest 0.417 at k = 2; Ward cophenetic correlation 0.786. Mining at 1% support: Apriori 0.027 s, FP-Growth 0.042 s, Eclat 0.020 s, identical results (6,396 itemsets). Eclat was fastest here, FP-Growth slowest. Times vary by machine.

**Not checked.** The pages were exercised with Streamlit's headless test runner, not looked at in a browser, so chart sizing and card alignment are untested by eye.

## What was broken (pages 1-4) and how it was fixed
| # | Problem | Fix |
|---|---|---|
| 1 | **Crop Advisor and What-if Lab always said "No soil assessment yet".** Soil Analysis stored `{id, values, categories}` but `utils/session.py` looked for N, P, K ... at the top level. | `session.py` now reads `assessment["values"]`; the storage format is documented in one place. |
| 2 | Dashboard "Clusters (K-Means)" card was a hardcoded default (4), not derived from data. | Replaced by calculated cards: records, crop classes, features, **saved assessments (counted from the database)**. |
| 3 | Dashboard "Recent assessments" always showed empty Predicted crop / Cluster columns; nothing wrote them. | Crop Advisor now stores the ID3 prediction and K-Means cluster on the saved row. |
| 4 | "New Soil Assessment" passed an absolute file path to `st.switch_page`. | Uses the same relative page path the navigation registers; default page no longer has a `url_path`. |
| 5 | What-if Lab: sliders came back at their **minimum** after visiting another page (Streamlit discards widget values when you leave a page). | Sliders reset from the saved assessment whenever their values are missing or the assessment changes; Reset button kept. |
| 6 | What-if Lab: "Preferred crop" defaulted to the alphabetically first crop (apple) unless Crop Advisor was opened first. | Defaults to the current ID3 prediction. |
| 7 | Dashboard and What-if Lab read a `kmeans_k` session key that no page ever set (so the cluster count was always the default). | The chosen k is stored in a plain session key (`selected_k`, which survives page changes) and used by Crop Advisor, What-if Lab and Cluster Explorer. |
| 8 | If the real CSV was missing, the generated sample data was saved **as** `Crop_recommendation.csv`, so the next run treated it as real and the warning vanished. | Sample data is saved as `synthetic_crop_recommendation.csv`; the Dashboard warns on every run until the real file is added. |
| 9 | ID3 accuracy was hidden in a collapsed expander; the split was not balanced per crop. | Held-out accuracy is a visible metric (80/20 split, same share of every crop). |
| 10 | Housekeeping: committed `__pycache__`, a stray UTF-16 `test_file.txt`, a test row in `data/agrimine.db`, outdated README. | Removed; `.gitignore` added; README rewritten. |

Checked and found correct (unchanged logic): ID3 entropy / information gain, K-Means, k-means++, dataset loading, input validation, categorisation.

## What was added
* **Pattern Mining**: Apriori from scratch (bitset counting, join + prune), sliders for support / confidence / pattern size, crop filter, sortable rules table (support, confidence, lift), top-10-by-lift chart, required caption. Defaults (support 1%, confidence 60%, size 5) give rules for all 22 crops and run in about 0.05 s.
* **Cluster Explorer**: K-Means with z-score and k-means++, selector for k, 2D map via PCA (NumPy SVD), cluster profile table, crop-by-cluster heatmap, nearest cluster to your assessment highlighted with a star, elbow plot and silhouette score (k = 2 to 10).
* **Data Insights**: SQLite star schema (`fact_crop_observation`, `dim_crop`, `dim_rainfall_category`, `dim_ph_category`, `dim_temp_category`), ETL function with a visible, stored log and row-count / foreign-key checks, Slice / Dice / Roll-up / Drill-down tabs running `GROUP BY` queries, SQL shown under each result. All database code is in `db/warehouse.py`.
* **UI**: theme in `.streamlit/config.toml`; all CSS, headers, sidebar brand and Plotly styling in `utils/style.py` (called on every page); rounded metric cards; one green palette.
* **Tests**: `tests/test_core.py` (algorithms vs brute force / hand calculation, warehouse queries vs pandas) and `tests/smoke_test.py` (opens every page with Streamlit's test runner).
* Page files renumbered to match the page list (`2_Soil_Analysis.py` ... `7_Data_Insights.py`).

## Verification status (please read)
The build environment could not install Streamlit or Plotly (package index blocked), so the app itself was **not launched** there. What was verified: the algorithms and database (including against scikit-learn / brute force / pandas as references), and every page script's logic by running it against a stand-in for Streamlit. What still needs one run on your machine: `python tests/smoke_test.py` and a visual look at the pages (the sidebar branding order and chart appearance depend on Streamlit's real rendering).

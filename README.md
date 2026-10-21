# AgriMine – Precision Agriculture

A crop advisor for farmers with a data mining toolbox for teachers, built for a Data Warehousing & Mining project.
A farmer enters a soil and weather check and gets the best crop, how well each reading fits it (Crop Doctor), and a Plan B.
The same numbers are open to inspection in the teacher pages, where each algorithm (ID3, Naive Bayes, K-Means with PCA, hierarchical
clustering with DIANA, Apriori, FP-Growth, Eclat, linear regression) is shown working. Every algorithm is written from scratch with
NumPy (**no scikit-learn, no scipy in the app**). The app is in English and Marathi, light and dark, and works on a phone.

It has three parts, all started by one command:

| Part | What it is | Where |
|---|---|---|
| **Web app** | the product: farmer pages and the five headline teacher pages | `web/` (Next.js, shipped prebuilt as `web/out`) |
| **API** | FastAPI; validates and shapes data, all logic is in `core/` | `api/` |
| **Technical lab** | the other technical pages, in Streamlit | `teachers-lab/` |

## How to run (needs Python 3.10 or newer, nothing else)
This is how the release zip (`agrimine-release.zip`) is used. It already contains the built web app, so Node is **not** needed.

    pip install -r requirements.txt
    python -m api              # open http://127.0.0.1:8000

That one command serves the web app and the API and also starts the technical lab on port 8501 (and stops it when you stop the API).
The data file is `data/Crop_recommendation.csv` (the Kaggle "Crop Recommendation" set: 2,200 rows; columns N, P, K, temperature, humidity, ph,
rainfall, label). If it is missing the app generates a sample file with the same columns, says so, and never invents numbers beyond that.
Saved checks go to `data/agrimine.db`, created on first run.

Useful settings: `AGRIMINE_DB=/path/to.db` (another database), `AGRIMINE_LAB=0` (do not start the lab), `AGRIMINE_LAB_PORT=8502`,
`AGRIMINE_LAB_URL=...` (the address browsers should use for the lab, if it is not `http://<same host>:<port>`), `--port 8001` (another web port).
The lab alone: `cd teachers-lab && streamlit run app.py` (or `make lab`).

## What is in the web app
Every page exists in English at `/en/...` and in Marathi at `/mr/...`. A page is about one soil check, chosen with `?check=N` (the newest check when omitted).

| Page | Address | What it does |
|---|---|---|
| Home | `/` | one-screen overview: best crop, top 3, soil health, Plan B, farms like yours, what each crop needs, what matters most, patterns found, model accuracy |
| New soil check | `check/` | validated form; saves the check and its prediction in one step |
| What should I grow? | `grow/` | the recommended crop, all 22 crops ranked, reasons, side-by-side comparison; readings can be edited to try values (nothing is saved) |
| Crop Doctor | `doctor/` | each reading against the range the chosen crop grows in: Good / Moderate / Needs attention, with advice |
| Plan B | `plan-b/` | pick a crop; if it is a weak fit, the crops that fit better and what each needs |
| All checks | `checks/` | every saved check |
| For teachers | `teachers/` | where each algorithm lives, the evaluation numbers, a link to each teacher page and to the technical lab |
| ID3 decision tree | `teachers/id3/` | the tree's answer, every question it asked with its information gain, held-out accuracy |
| Naive Bayes | `teachers/naive-bayes/` | Naive Bayes against ID3, which readings pushed the decision, Bayes' formula worked out with your numbers |
| K-Means | `teachers/kmeans/` | k groups on a PCA map, group profiles, crops per group, elbow and silhouette |
| Apriori | `teachers/apriori/` | association rules at the support, confidence and size you choose |
| Hierarchical | `teachers/hierarchical/` | the 22 crops as a dendrogram (four linkages), k clusters, top-down DIANA |

The teacher pages show the same numbers as the farmer pages (tests compare them), because both read from `core/`.

## The technical lab (Streamlit)
It opens on **For teachers**, which lists every technical page: Crop Advisor (ID3), Model Council (Naive Bayes), Cluster Explorer
(K-Means + PCA), Hierarchical, Pattern Mining (Apriori), FP-Growth and Eclat, Water Lab (regression), Data Insights (OLAP star schema),
Data Lake, Data Prep, What-if Lab and Soil Analysis. The first five are also in the web app; the last seven exist only here.
The lab no longer has its own Home, What should I grow?, Crop Doctor or Plan B: those are in the web app only (a test checks this).
The web app's For teachers page links to each lab page on the current check.

## The API
Docs at `/docs`, contract at `/openapi.json`; `python -m api.export` rewrites `api/openapi.json` after a schema change (a test fails if you forget).
All routes are under `/api`: `GET /meta`, `POST /checks` (validate, predict and save in one transaction), `GET /checks`, `GET /checks/{id}`,
`POST /recommend` (stateless), `POST /doctor`, `POST /plan-b`, `GET /insights/farms|needs|gain|patterns|accuracy`, `GET /lab`, `GET /health`, and the teacher
pages' data: `POST /teachers/id3|naive-bayes|kmeans`, `GET /teachers/apriori|hierarchical`. Every error has one shape: `{code, message, field, errors}`.
On start-up the API trains the models (about 2 s), migrates an older `assessments` table and predicts any saved check that has none.

## Deploying: API on Render, web app on Vercel
The web app and the API are one origin when `python -m api` serves `web/out`. If the web app is hosted somewhere else (Vercel), the browser calls the API
from another origin and sends an OPTIONS "preflight" first; it only goes on if the answer has `Access-Control-Allow-Origin`.
* **Render (the API).** `render.yaml` is a blueprint; on an existing service set the same things by hand. Build command `pip install -r requirements.txt`,
  start command `python -m api` (it listens on `0.0.0.0` and `$PORT` when `PORT` is set, which Render does), health check `/api/health`.
  The lab (Streamlit) is off on Render by default. Saved checks live in a SQLite file on the service's disk, which a free service loses when it restarts.
* **CORS.** The allowed origins are `http://localhost:3000`, `http://127.0.0.1:3000` and `https://agrimine.vercel.app`. Change them without touching the code:
  `AGRIMINE_CORS_ORIGINS=https://my.site,https://other.site` (comma separated, no path), and `AGRIMINE_CORS_ORIGIN_REGEX=https://agrimine-.*\.vercel\.app`
  to allow Vercel's preview addresses too. Every answer carries the headers, errors included; an unexpected crash is a JSON 500 (`server_error`), not a bare failure.
* **Vercel (the web app).** Set `NEXT_PUBLIC_API_URL=https://agrimine.onrender.com` (no trailing slash). It is baked in at BUILD time: after changing it, redeploy.
* **Is it really running my code?** `GET /api/health` shows `"commit": "<first 7 letters>"` on Render. To test the whole chain the way a browser does, from your machine:
  `python tools/check_cors.py https://agrimine.onrender.com` (it waits for a sleeping free service, then sends the preflight and a GET with your web app's Origin and says what is wrong).
  A free Render service sleeps after 15 minutes and needs up to a minute to wake; while it wakes, Render's proxy answers 502/503 WITHOUT CORS headers, and the browser reports that as a CORS error.

## Developing (needs Node as well)
    make install       # Python + Node dependencies
    make build         # next build -> web/out
    make api           # the API, the built site and the lab
    make dev           # API on :8000 + Next dev server on :3000 with hot reload
    make contract      # after changing an API schema: regenerate api/openapi.json and web/lib/api/schema.d.ts
    make test          # Python + web unit + browser tests
    make release       # build, then pack dist/agrimine-release.zip

`web/` is Next.js 16 (static export), React 19, Tailwind 4, Base UI components, Lucide icons, Plus Jakarta Sans (and Noto Sans Devanagari for Marathi).
Browser tests (Playwright) start their own servers with throw-away databases, one group per project (`web/playwright.config.ts`). Run whole files
(tests in a file share state on purpose) and, on a small machine, **one project at a time** (`npx playwright test --project=pages`); running all projects
at once can exhaust the machine's threads.

## The Marathi text
The Marathi wording and the Marathi crop names are drafts. Please have a Marathi speaker (ideally farmers) check them before they are shown to farmers.
Translations for the web app are in `web/lib/i18n/dictionaries/` (`en.json`, `mr.json`; a test checks that both have the same keys and that none is unused).

**How the farmer numbers are made** (all in `core/advice.py`, nothing typed in):
* *Best crop* = the crop with the highest Gaussian Naive Bayes probability (a class probability, not calibrated, not a yield forecast); the ID3 tree gives a second opinion.
* *Match score* (0 to 100, Top 3 and Plan B) = how close your readings are to each crop's average, in units of that crop's own spread: 100 / (1 + mean distance). A similarity score.
* *Soil health* = each reading against the crop's records: inside the 10th to 90th percentile = Good, inside its observed min to max = Moderate, outside = Needs attention.
* *Farms like yours* = K-Means groups (all seven readings) drawn on rainfall and temperature; your field is the red X.

## How the algorithms work (plain language)
* **ID3** (`algorithms/id3.py`): numbers are cut into 5 equal-frequency bins. At each node the
  tree picks the feature with the highest *information gain* (drop in *entropy*, i.e. how mixed
  the crops are) and splits on it. Accuracy is measured on a 20% hold-out the tree never saw.
* **Apriori** (`algorithms/apriori.py`): every row is a basket of items such as `rainfall=high`,
  `ph=acidic`, `crop=rice`. It finds item groups whose *support* (share of rows) is above a
  threshold, growing them one item at a time and discarding any group with a rare subset. Rules
  are scored by *confidence* and *lift*.
* **K-Means** (`algorithms/kmeans.py`): z-score standardise, choose starting centres with
  k-means++, then repeat "assign rows to the nearest centre / move centres to the cluster mean".
  The elbow plot shows *inertia*; the *silhouette score* shows how well separated clusters are.
* **PCA** (`algorithms/pca.py`): NumPy SVD finds the two directions with the most variance so 7
  features can be drawn on a 2D map (and, on Data Prep, how many are really needed).
* **Naive Bayes** (`algorithms/naive_bayes.py`): Gaussian. Class priors, per-class mean and variance
  of every feature (plus a tiny variance floor), a sum of log-likelihoods and a softmax for the
  probabilities. `explain()` shows which feature favoured the winner over the runner-up.
* **Regression** (`algorithms/regression.py`): simple regression in closed form (slope = cov / var),
  multiple regression with `np.linalg.lstsq`; R-squared, adjusted R-squared and RMSE, scored on a
  held-out 20%.
* **Hierarchical** (`algorithms/hierarchical.py`): agglomerative clustering with single, complete,
  average and Ward linkage (Lance-Williams updates), a scipy-style linkage matrix, `cut_tree`,
  cophenetic correlation, a dendrogram layout for Plotly, and divisive clustering (DIANA,
  splinter-group method). The 22 crops are clustered on their standardised mean profiles.
* **FP-Growth and Eclat** (`algorithms/fpgrowth.py`): FP-tree with header-table chains and
  conditional pattern bases; Eclat on the same bitsets as Apriori; `closed_itemsets` and
  `maximal_itemsets`. All three miners use the same item numbering and return the same
  `{itemset: count}`. On this small dataset, in pure Python, FP-Growth is the slowest of the three
  (the page shows the measured times); it is not claimed to be faster.
* **OLAP** (`db/warehouse.py`): a star schema (`fact_crop_observation` + `dim_crop`,
  `dim_rainfall_category`, `dim_ph_category`, `dim_temp_category`) filled by an ETL function.
  Slice = fix one dimension, dice = filter several, roll-up / drill-down = remove / add a
  `GROUP BY` column.

## Categories used everywhere
low / medium / high = bottom / middle / top third of the records (rainfall, temperature, N, P,
K, humidity). pH is acidic (< 6.0), neutral (6.0 to 7.0) or alkaline (> 7.0).
They are defined once in `core/preprocessing.py`.

## Project layout
    core/                   pure Python: NO Streamlit (a test proves it), reusable by any front end or API
      algorithms/           id3, naive_bayes, regression, kmeans, pca, hierarchical, apriori, fpgrowth
      db/warehouse.py       ALL database code (assessments, star schema, ETL, OLAP queries)
      features.py           the one description of the 7 measurements (names, Marathi names, units, ranges)
      crops.py              the one description of the 22 crops (names, Marathi farmer names, family)
      advice.py             crop ranking, soil health, tips, cluster summaries (the farmer rules)
      models.py             trained models and tables, cached with core/cache.py
      preprocessing.py      dataset loading, validation, categories, data-prep helpers
      lake.py               data lake files (raw, curated, catalog)
      cache.py              @cached: a tiny thread-safe cache replacing st.cache_* in the logic layer
      checks.py             a soil check = readings + prediction, created and saved in one transaction
    api/                    FastAPI layer: routers/, schemas.py (the contract), errors.py, state.py (warm-up), openapi.json
      teachers.py           what the teacher pages show, as plain data (one function per page)
    web/                    the front end (Next.js): app/[lang]/, components/ (ui, farm, home, grow, doctor, teachers), lib/ (api client, i18n, charts), e2e/
    teachers-lab/           the Streamlit technical lab: app.py (entry point), pages/ (2_ ... 13_ and 17_ For teachers), utils/, assets/, .streamlit/
    tools/                  make_release.py (packs the release zip)
    data/                   the CSV (the SQLite file and data/lake/ are created on first run)
    docs/                   ARCHITECTURE_PLAN.md (the plan and its progress log)
    tests/                  test_core.py, test_api.py, test_lab_links.py, test_lab_process.py, test_release.py, test_web_glyphs.py, smoke_test.py (opens every lab page)

## Switching the database to MySQL later
Only `db/warehouse.py` talks to the database. The changes are listed at the top of that file:
`connection()`, the `PARAM` placeholder (`?` -> `%s`), `_table_names()` (use `SHOW TABLES`) and
the `CREATE TABLE` types (`INTEGER PRIMARY KEY` -> `INT PRIMARY KEY`, `REAL` -> `DOUBLE`,
`TEXT` -> `VARCHAR`, `AUTOINCREMENT` -> `AUTO_INCREMENT`).

## Tests
    python -m pytest -q tests       core, API, lab links, lab process, release, crop drawings (hierarchical clustering is compared with scipy when it is installed)
    python tests/smoke_test.py      opens every lab page, its controls and the language toggle with Streamlit's test runner
    make test-web                   type check, lint, unit tests of the web app
    make test-e2e                   browser tests against the real product: every page, English and Marathi, light and dark, phone sizes,
                                    accessibility (axe) and keyboard checks, screenshot comparisons, and the real lab

`scipy` is an **optional test dependency** (`pip install -r requirements-test.txt`); the app does not need it.

## Notes and limits
* Association rules and clusters describe the historical data; they are not causal advice.
* The What-if Lab simulates model behaviour; it does not guarantee real soil outcomes.
* Accuracy, R-squared, silhouette and run times shown in the app are computed when the app runs, never typed in.
* A check is saved together with its prediction when it is created (`POST /api/checks`); older rows are predicted when the API starts.

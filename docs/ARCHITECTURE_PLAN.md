# AgriMine: architecture plan (today -> target)

Status: proposal for review. Nothing in this document is built yet. Numbers marked (measured) were measured on the current code.

## 0. Constraints and what we do not know

| Known | Source |
|---|---|
| Farmer-first Home, five sidebar items, algorithms kept under "For teachers", English / Marathi toggle, no invented numbers | Hretz's brief |
| Algorithms written from scratch with NumPy, no scikit-learn, no scipy in the app | Hretz's first brief |
| Hretz agreed to the new code shape (Next.js frontend, Python core) | Lucas, in the thread |
| **Unknown:** the teacher's own assignment text and marking rubric; whether the code is run or only demoed; whether a Node frontend is allowed | never seen |

Rule that follows: the Python core and the Streamlit lab stay runnable on their own, so a Python-only submission is always possible. The Next.js app is an additional front end, never a hard dependency of the algorithms.

## 1. Today

```
streamlit run app.py
   browser <--websocket--> ONE Python process
                             app.py + 17 pages/*.py   (each page = a script re-run on every click)
                             utils/ (11 modules: logic + caching + CSS + translation, mixed)
                             algorithms/ (pure NumPy)      db/warehouse.py (SQLite, the only DB code)
```

What works and stays: `algorithms/` (1,607 lines with `db/`, tested, no UI), `db/warehouse.py`, the dataset, the 33 tests.

Where it is bolted on and fails (from the audit):
1. Two stylesheets stacked (about 80 KB of CSS injected on every rerun, 12 `!important`, `:has()` selectors on Streamlit's internal DOM).
2. Components are f-strings; charts need CSS height hacks; layout bugs were invisible to the tests (screenshots found them).
3. Navigation is hand wired (hidden `st.navigation`, global registry, 22 hard-coded page paths, 8 `try/except` for pages opened without the nav).
4. Logic leaks into UI: the crop-fit score exists twice, crop profiles are computed in 3 places, feature labels are defined in 9 places, Home writes to the database while rendering.
5. Translation covers only the farmer pages; no test stops hard-coded text.
6. Fonts are not shipped; icons are emoji; 10 of 22 crops share one seedling.

## 2. Target

```
production:   uvicorn api.main:app                (ONE process, ONE command)
   browser --HTTP/JSON--> FastAPI ---serves---> web/out/  (static export of the Next.js app)
                             |
                             +--> core/  (pure Python: algorithms, advice, db, i18n data)
development:  Next dev server (hot reload)  --proxy-->  FastAPI --> core/
teachers lab: Streamlit (kept) ---------------------------------> core/      (separate process, linked from the app)
```

Repository layout (git history kept, `git mv` not copy):

```
core/                      pure Python, no Streamlit, no FastAPI
  algorithms/              moved as is (id3, naive_bayes, kmeans, pca, hierarchical, apriori, fpgrowth, regression)
  db/                      warehouse.py as is; adds checks repository
  advice/                  ranking.py  doctor.py  planb.py  clusters.py  tips.py   (one definition of each rule)
  features.py              ONE registry: key, label_en, label_mr, unit, valid range, icon, order
  crops.py                 crop key, label_en, label_mr, family, glyph id
  data/                    Crop_recommendation.csv
api/
  main.py  routers/  schemas.py (pydantic)  deps.py  state.py (models trained once at startup)
web/                       Next.js 16, React 19, TypeScript, Tailwind 4
  app/[locale]/            page.tsx (Home)  grow/  doctor/  plan-b/  teachers/
  components/ui/           shadcn-style components built on Base UI (button, tabs, select, tooltip, dialog, switch, toggle-group)
  components/farm/         StatCard, Hero, CropRow, GaugeRow, Ring, ChartCard, Sidebar, ProfileBar
  lib/api/                 types GENERATED from the OpenAPI schema
  messages/en.json mr.json
  public/fonts  public/art  public/crops/*.svg
teachers-lab/              the 12 existing Streamlit pages, importing core/
tests/                     core/  api/  contract/  e2e/
docs/
```

### 2.1 Stack (versions checked on npm today; pin exact versions in the lockfile)
Next.js 16.4, React 19.3, Tailwind 4.3, `@base-ui/react` 1.9 (headless primitives), `lucide-react` (interface icons), Recharts through the shadcn chart wrapper, `next-intl` 4.x, `@fontsource/plus-jakarta-sans` + `@fontsource/noto-sans-devanagari`. Python: FastAPI, pydantic v2, uvicorn, plus the current numpy / pandas / plotly (plotly only in `teachers-lab/`).

### 2.2 Why FastAPI and not Next route handlers
The algorithms are Python. Re-implementing them in TypeScript would duplicate the part the assignment is graded on. A thin API keeps one source of truth.

### 2.3 Why a static export served by FastAPI
One process and one command for Hretz and the teacher, no Node at run time, no CORS in production. The cost: no server-side rendering and no Next API routes. This app needs neither (pages are the same for everyone and data comes from the API).
Consequence: a check is addressed as `/?check=18` (query parameter), not `/checks/18`, because static export cannot enumerate dynamic ids.

## 3. Data and state

Measured (cold, one process): load data 0.01 s, ID3 0.07 s, Naive Bayes 0.01 s, K-Means for k=3,4,5 0.08 s, PCA 0.10 s, Apriori rules 0.11 s, miner benchmark 0.31 s, **K-Means diagnostics k=2..10: 3.4 s**, total cold start about 5 s. A warm recommendation takes about 7 ms and its JSON is about 1.6 KB; the 2,200-point scatter is about 38 KB.
Decisions that follow:
- Train everything once in the FastAPI lifespan and keep it in memory (`api/state.py`). No job queue, no cache invalidation.
- Compute the 3.4 s diagnostics in a background thread at startup; the Teachers pages wait on it, Home does not use it.
- The benchmark is measured once at startup and labelled with the machine and date, never typed in.

A soil check becomes a server record. Today a check is a session value plus a database row, and "saved" and "predicted" can be out of step (the "None" bug).

```
assessments(id, created_at, N, P, K, ph, temperature, humidity, rainfall,
            predicted_crop NOT NULL, probability, id3_crop, cluster_id, model_version)
```
- `POST /api/checks` validates, predicts and stores in one transaction. The state "saved but not predicted" cannot exist; the sidebar's "Saved only" example in the design lab disappears, or is kept only for rows migrated from the old schema (`predicted_crop IS NULL` is shown as "Pending").
- The current check is the `?check=` parameter, restored from the API on reload. No client-side global state beyond language and theme (localStorage).
- Migration of the existing `assessments` table: add the new columns nullable, backfill by running the predictor once.

## 4. API contract (v1)

| Method and path | Purpose | Replaces today |
|---|---|---|
| `GET /api/meta` | counts, crops (key, labels, family), feature registry, languages | `get_data`, scattered label dicts |
| `POST /api/checks` | create + predict + save | Soil Analysis save + Crop Advisor write |
| `GET /api/checks?limit=` , `GET /api/checks/{id}` | recent / one | `get_recent_assessments` |
| `POST /api/recommend` | stateless: values -> best crop, probability, ranking, ID3 opinion, reasons | `advice.recommend` |
| `POST /api/doctor` | values + crop -> per-reading status, usual range, tips, overall | `advice.soil_health` |
| `POST /api/plan-b` | values + preferred crop -> level, alternatives, needs | `match_scores` + Plan B page |
| `GET /api/insights/farms?k=` , `/needs` , `/gain` , `/patterns` , `/accuracy` | Home cards | `charts.py` data parts |
| `GET /api/lab/...` | data for teacher pages, only for ported ones | Streamlit pages |

Rules: every response is a pydantic model; the OpenAPI schema is the contract; `web/lib/api/types.ts` is generated from it (`openapi-typescript`); a contract test regenerates it and fails on drift. Errors use one shape `{code, message, field?}`. Inputs are validated with the ranges from `features.py`.

Open design points to settle with Hretz: the ranking definition, below.

## 5. Domain rules to fix while moving (defects, not features)

1. **One ranking.** Today rank 1 is the Naive Bayes pick and ranks 2-3 are profile-match scores: two different scales. Proposal: rank every crop by the Naive Bayes posterior, show the profile match as a separate, labelled "similarity" bar. Needs Hretz's agreement.
2. **Honest probabilities.** Naive Bayes gives 99.7% vs 0.3%: it carries little information. Label it "model probability, not a guarantee", and say in For teachers that the Kaggle set is clean (about 100 rows per crop) so 99.5% accuracy says little about real fields.
3. **"Soil health" means typical for this crop in the dataset**, not an agronomic standard. Keep the wording, keep the tips as "general guidance", and have the tips reviewed before they reach farmers.
4. **Units.** N, P, K are shown without "kg/ha" until Hretz confirms the source unit.
5. **Silhouette is 0.25** for the K-Means groups: describe them as "similar conditions", not "farms like yours that grow X".
6. **Sidebar badges** (for example Crop Doctor "Good") need one defined meaning (best crop? chosen crop?).
7. **Marathi crop names** are missing; add `label_mr` per crop and have a Marathi speaker review all strings.

## 6. Frontend architecture

- **Design tokens** live in one place: Tailwind `@theme` in `globals.css` (colour roles, radius scale, shadow scale, type scale, spacing). Light and dark are two sets of CSS variables on `data-theme`; components use only roles (`bg-card`, `text-muted`, `ring-line`), never raw colours. The tokens are the ones used in the design lab.
- **Components:** `components/ui/*` are written against Base UI primitives (the shadcn registry is not reachable from our build sandbox, so they are vendored by hand and can later be regenerated with the real CLI); `components/farm/*` compose them. Every component has typed props and one Storybook-style test page (`/dev/components`) used by the visual tests.
- **Fluid sizing:** rem everywhere, root font `clamp(14px, min(1.04vw, 1.56vh), 24px)` (as in the lab), no content max-width, grid for layout. Home keeps one screen at 1366x768 up to 2560x1440, scrolling the sidebar's middle section rather than the page.
- **Charts:** Recharts for bars and areas; custom SVG for dendrogram, rings, hatch bars and the crop-needs bubbles; canvas (or 600-point sampling) for the 2,200-point scatter. Chart colours are tokens.
- **Icons and imagery:** `lucide-react` for UI; 22 hand-drawn crop SVGs in one consistent style (8 exist in the lab); the sidebar landscape as two transparent files (day, night) already produced.
- **Fonts:** Plus Jakarta Sans (Latin) and Noto Sans Devanagari (Marathi), self-hosted via `@fontsource`. If Jakarta disappoints, Inter or Geist is a one-line change.
- **i18n:** `next-intl`, `messages/en.json` and `mr.json`, route prefix `/en` and `/mr`; units and crop keys never translated, crop display names come from `crops.py`. A test fails the build if a user-visible string is not a message key and if the two files have different keys.
- **Accessibility:** WCAG AA contrast checked per theme by an automated test, keyboard order, visible focus, reduced-motion respected.

## 7. Streamlit's future

`teachers-lab/` keeps the 12 technical pages, importing `core/` instead of `utils/`. It is linked from "For teachers" and runs as a separate process (`streamlit run teachers-lab/app.py`). Pages are ported to Next one at a time in the order the professor will demo them; a page is only removed from the lab after its replacement passes the same tests. The current Streamlit farmer pages (Home, grow, doctor, Plan B) are removed once the Next versions ship.

## 8. Testing

| Layer | Tool | Gate |
|---|---|---|
| core (algorithms, advice, db) | pytest | the 20 existing core tests move unchanged; add tests per rule in section 5 |
| API | pytest + httpx | every endpoint, validation errors, the "saved implies predicted" invariant |
| contract | openapi-typescript + `tsc` | generated types match the schema |
| components | Vitest + Testing Library | props, states, a11y roles |
| end to end | Playwright | save a check, see Home, switch language, open each page; screenshot diffs at 1366x768, 1536x1024, 1920x1080 in light and dark |
| translation | script | key parity, no hard-coded strings |
| performance | Lighthouse CI (informal) | Home loads under 2 s on the dev machine |

The headless-only testing of today missed every layout bug; screenshot diffs are the main addition.

## 9. Delivery and run instructions (target)

```
pip install -r requirements.txt
python -m api            # serves the API and the prebuilt site on http://localhost:8000
make dev                 # developers: FastAPI + Next dev server
make build               # next build (static export) into web/out
streamlit run teachers-lab/app.py   # optional technical lab
```
The prebuilt `web/out/` is committed to release zips, so a Python-only machine can run the product.

## 10. Migration plan (no big bang; Streamlit keeps working until cut-over)

| Phase | Work | Exit criteria | Rough effort |
|---|---|---|---|
| 0 | Freeze decisions in section 12; fix section 5 defects in the current code | tests green, Hretz agrees ranking and labels | 1 day |
| 1 | Extract `core/` (git mv), feature + crop registries, remove Streamlit from logic | 33 tests green with Streamlit uninstalled in core | 1-2 days |
| 2 | `api/` for `meta`, `checks`, `recommend`, `doctor`, `plan-b`, `insights/*`; startup training; migration of `assessments` | API tests + contract generation green | 2 days |
| 3 | `web/` scaffold, tokens, fonts, icons, Base UI components, `/dev/components`, light + dark | component tests + first visual baselines | 2-3 days |
| 4 | Home on real data | e2e: create a check, Home shows it; one-screen at three sizes | 2 days |
| 5 | What should I grow?, Crop Doctor, Plan B | e2e per page, translation gate | 3 days |
| 6 | Marathi review, 22 crop glyphs, accessibility pass | reviewer sign-off, contrast test green | 2 days |
| 7 | For teachers hub; `teachers-lab/` re-pointed to `core/`; port the pages the professor will demo | each ported page passes its old test | 2-4 days |
| 8 | Cut-over: remove old Streamlit farmer pages, release zip with prebuilt `web/out`, docs | clean-machine run from the README | 1 day |

Estimates are my own guesses for one focused person and assume no surprises with Base UI or `next-intl` under static export; treat as +/- 50%.

### Progress log
- **Phase 0 (done, Oct 20):** ranking by Naive Bayes probability with similarity separate; Marathi farmer crop names (draft); N, P, K without units; one shared similarity score.
- **Phase 1 (done, Oct 20):** `core/` extracted with `git mv` (history kept): `algorithms/`, `db/`, `preprocessing`, `models`, `advice`, `lake`, plus new `cache.py`, `features.py`, `crops.py`. Streamlit is gone from `core/` (a test runs a recommendation in a fresh interpreter where Streamlit cannot be imported). The 9 duplicated label dictionaries and the scattered crop tables are replaced by the two registries. 46 tests pass; the Home page differs from before the refactor by 3 pixels out of 1.57 million (antialiasing).
  Two adjustments to the layout above: the dataset stays at `data/Crop_recommendation.csv` (README and users already rely on that path) and `advice.py` is still one module (it will be split into `advice/` when the API needs it).

- **Phase 2 (done, Oct 20):** `api/` with 12 routes (meta, checks, recommend, doctor, plan-b, insights x5, health), pydantic schemas generated from the feature registry (readings carry min/max in the schema), one error shape, start-up warm-up, `core/checks.py` (a check is created, predicted and saved in one transaction), migration and backfill of the old `assessments` table, `api/openapi.json` committed with a drift test. Measured on a real uvicorn process: start-up to first answer 2.4 s, every endpoint 2-7 ms warm. 10 API tests.
  Two things found only by running the real server: a cache without a lock repeated a 3.4 s computation for a concurrent request (fixed: `core/cache.py` is now thread-safe, with a test) and the farms payload was 140 KB as objects (now 32 KB as `[rainfall, temperature, cluster]` triples). `GET /insights/farms` uses a per-k silhouette (`kmeans_silhouette`) instead of the 2..10 table so Home never waits.
  Not yet done from section 4: `GET /api/lab/...` (teacher pages; Phase 7) and a Marathi translation of the tips (they are English only in `/doctor`).

- **Phase 3 (done, Oct 20):** `web/` scaffolded with Next.js 16.4, React 19.3, Tailwind 4.3, `@base-ui/react` 1.9, Lucide, Recharts (installed, not used yet), `@fontsource` fonts. Design tokens as CSS variables with light and dark in `globals.css` (components use roles such as `bg-card`, never raw colours); fluid rem sizing; Base UI based Button, IconButton, Segmented, Tooltip, Track (Progress), Badge, Card; farm components StatCard, CropRow, CropGlyph (8 of 22 drawn), Sidebar with the transparent landscape and ProfileBar; typed API client with types generated from `api/openapi.json`; hand-rolled i18n (`en.json`/`mr.json`, key and placeholder parity tested); a component gallery at `/en/dev/components/`.
  Tests: 20 unit and contract tests (Vitest), ESLint and `tsc` clean, 11 browser tests (Playwright against the real FastAPI process serving `web/out`): 7 visual baselines (light and dark at 1366x768, 1536x1024, 1920x1080, plus Marathi dark), language switch, theme persistence, accessible names, one-process serving. The visual tests passed twice in a row against saved baselines.
  Things this Next.js version did differently from what I expected (all in `node_modules/next/dist/docs`): the template turns on Cache Components, which is a server-caching feature and is switched off for a static export; the root layout lives in `app/[lang]/layout.tsx` so `/` cannot be a page and is `public/index.html` (a redirect to the saved language); route-aware props types (`LayoutProps<"/[lang]">`) come from `next typegen`; `next-intl` was not needed (a 60-line provider covers it, and the plan's fallback was the right call); Tailwind's `dark:` variant had to be pointed at `data-theme` or it follows the operating system instead of the switch.
  Not yet: no farmer page exists in `web/`; the sidebar links to routes that are built in phases 4 and 5.

- **Phase 4 (done, Oct 20):** Home on real data in `web/`, plus the "New soil check" form. Every number on Home comes from the API: summary cards (`/meta`, `/checks`), hero, Top 3 and Plan B (`/recommend`), Crop Doctor card (`/doctor`), farms and needs charts (`/insights/farms`, `/insights/needs`, hand-drawn SVG with a collision-free label placer), information gain, patterns (with the real rule count, no longer typed), accuracy. A saved check goes to `/en/?check=N`; the sidebar and links keep the id; with nothing saved every card explains itself instead of spinning. States covered: loading, empty, error with retry, unknown check id, bad reading refused next to its field.
  Tests added: 22 unit (chart scales and ticks, label placement, label/format helpers, `useCurrentCheck`), 12 browser (empty state, validation, save, "Home equals the API", Marathi names, switching checks, retry after a failed card, six cards fit one screen at two sizes, 3 visual baselines). Totals: 47 unit, 23 browser, 57 Python.
  **Test-quality findings, found by trying to break my own tests:** (1) the visual tolerance of 0.3% let a changed sentence pass as "the same" and left a stale baseline in place; it is now 40 pixels, and a deliberate one-sentence edit makes 2,058 pixels differ and fails the test; the baselines were rebuilt and are stable over 3 runs. (2) A mutation that removed the label-overlap rule was not caught by the test named for it; a search found an input where only that rule matters (`Rice`/`Coffee` at the same spot) and the test now uses it. (3) A mutation that accepted `?check=-5` was not caught; the test now covers `-5`, `7.5`, `1e3`, `0x10` and empty.
  API changes made along the way (contract regenerated, drift tests green): `/insights/patterns` returns `{total, items}`; `/insights/accuracy` returns the split seed as a number instead of an English sentence; `/meta` returns crop families with Marathi names.
  **Bug found afterwards (reported by Lucas, Oct 20):** the sidebar was `h-screen` but not `sticky`, so it scrolled away with the page and left an empty column with the landscape and profile bar floating mid-page (top at -424 px after scrolling at 1366x768). My tests never scrolled: the screenshots were taken at scroll 0 or as one stitched full-page image. Fixed with `sticky top-0 self-start`; new browser tests scroll to the middle and the bottom at 1366x768 and 1536x1024 and require the sidebar to stay at the top, fill the window and keep the profile bar on screen (checked to FAIL on the old code: off by 212 px). Lesson recorded: any layout claim about scrolling needs a test that scrolls. Totals now: 47 unit, 25 browser, 57 Python.
- **Phase 5 (done, Oct 21):** What should I grow?, Crop Doctor, Plan B and a first For teachers page in `web/`, all on the API. Shared pieces: `useReadings` (the current check's values, or the dataset medians when nothing is saved; editable, nothing is saved; debounced, validated before any request), `ReadingsEditor`, `CropSelect`/`Select` (Base UI), `CompareTable`, `Gauge`, `rangeText` (the unit once: "20.9-26.5 C"). The sidebar chip is now defined and wired: **overall soil health of the recommended crop for the check you are looking at**; absent when nothing is saved (resolves the open point in section 5.6). Doctor tips are translated in the web app: the API sends a stable `tip_key` (e.g. `P.high`), the dictionaries hold the wording (Marathi: draft, farmers review). `/meta` now carries each reading's dataset median (`default`).
- **Sidebar rework (Oct 21):** the landscape now owns its own flex region at the bottom; the current-check card and recent list scroll above it (keyboard-focusable region), so nothing is drawn over the picture at any window height (tested 1920x1080 down to 1366x500 by hit-testing, not just by eye). Removed the dead search box and chevron; "View all checks" opens a real list (`/checks/`); a recent check keeps you on the page you are on (Home when you are on a check/list page). New `sidebar` test group (own server and DB) with 4 baselines. Lesson: a layout test must put the content in the situations that break it (short windows, a long list), and every new test is proven by breaking the code once.
- **Phase 6 (Oct 21): glyphs and accessibility done; Marathi review still needs the farmers.** All 22 crops now have a drawing (`glyph-data.ts`; `tests/test_web_glyphs.py` fails when a crop has none, a unit test fails when two crops share a picture). Accessibility is measured on the rendered pages with axe-core (`web/e2e/a11y.spec.ts`, own server group `a11y`): every page x light/dark x English/Marathi, WCAG 2 A/AA. It found one kind of defect, colour contrast in light mode (grey secondary text 3.7-3.95:1, status badge text 4.2-4.5:1, white on the main green button 4.38:1, the faded Plan B line); fixed by darkening five tokens (`--ink-3`, `--brand`, `--mint-ink`, `--butter-ink`, `--coral-ink`) and removing the opacity. Also tested: every tabbable control changes its look when focused (proved by removing focus rings on purpose: the test fails), and a new skip-to-content link works with the keyboard. Open for sign-off: the Marathi wording (all of `mr.json` is still a draft, including the new skip-link text) and the 22 drawings (the mango still reads a little like a peach).
- **Phase 7a (Oct 21): the Streamlit app now lives in `teachers-lab/`** (`git mv` of app.py, pages/, utils/, assets/, .streamlit/; nothing else changed in them). It imports `core/` by putting the parent folder on the import path; `make lab` runs it from that folder. The smoke test (all 16 pages) and test_core point at the new place; a deliberately broken page makes the smoke test fail, so it really opens the moved pages. Next: 7b lab reads the saved checks from `core.checks` (`?check=N` or the newest) instead of its own session state; 7c remove the farmer pages from the lab (their Next versions exist); 7d port the pages the professor demos.
- **Phase 7b (Oct 21): lab and web share the current check.** `teachers-lab/utils/session.py` now finds the current assessment in this order: `?check=N` in the address (read through `core.checks`), the one remembered in the session (the lab's own links drop the address, so the first page stores it), the newest saved check, none. The web's For teachers page has an "Open in the lab" link per algorithm (`web/lib/lab.ts`: `NEXT_PUBLIC_LAB_URL`, default http://localhost:8501) that carries the check id; `tests/test_lab_links.py` fails if a link names a page the lab does not have. Tests: 6 for the lookup (each rule broken on purpose, each break caught), 1 browser test for the links. Known Streamlit quirk, not ours: the FIRST deep link after the lab starts shows a "Page not found" dialog once (Streamlit learns its pages when the script first runs); later visits are clean. Still to do: 7c remove the farmer pages from the lab; 7d port to Next the pages the professor demos (needs Lucas's / Hretz's list).
- **Phase 7b, made to actually work (Oct 21).** The first version of the links pointed at `localhost:8501` but nothing started a lab: from `make api` the link went nowhere (checked: connection refused). Now `python -m api` starts the lab itself (`api/lab.py`: its own folder, port 8501, stopped with the API, killed with it on Linux if the API dies hard), warms it by connecting once like a browser (that makes Streamlit register its page addresses; without it the first link shows a "Page not found" dialog, proved by switching the warm-up off), and `GET /api/lab` reports `available` (answering AND warmed) and `url` (the host the browser used). The web links appear only when it is available; otherwise the page says how to start it. Tests: 6 process tests (disabled; already running -> use it; exact command and folder; stops with the API; not available until warmed; address; Streamlit missing), each broken on purpose and caught; 5 browser tests against a REAL lab (own group `lab`, port 4177 + Streamlit on 8177): click the link, the lab opens on that check, no dialog, newest check without `?check=`.
  Tests: 52 unit (adds message-key usage: no dead or missing keys), 46 browser in two isolated groups (`home` and `pages`, each with its own server and database), 57 Python.
  **Test-harness findings this phase, all fixed:** (1) the two spec files shared ONE database and raced for "check #1" when run in parallel: each group now has its own server and database; (2) screenshots raced with the sidebar's own data (current check, Crop Doctor chip load after the page): the helper now waits for them, language-independently; (3) running one test of a stateful group with `-g` shows the empty state, not a bug: the notes say to run whole files; (4) an unused-key test found 9 dead strings, a Marathi digit-consistency test found 9 strings mixing ७ with 5; (5) accepting changed baselines blindly (`--update-snapshots=changed`) hid a real layout bug (a chip made one nav row 2.8 px taller and shifted everything below): rows now have one fixed height, with a test that measures them, and every baseline update is followed by a per-file diff against the committed version.
  Not yet: the full interactive technical pages (phase 7); the crop-requirements rings of the old Home; 14 of 22 crop drawings; the Marathi text (farmers); a phone layout.
  Not yet (earlier note): Home has no check-specific page for "What should I grow?", "Crop Doctor", "Plan B" or "For teachers" (phases 5 and 7), so those sidebar links and the hero's arrow lead to pages that do not exist in `web/` yet; the sidebar's Crop Doctor status chip is not wired (its meaning is still an open design point, section 5.6).

## 11. Risks

1. The teacher may require Streamlit or a Python-only run. Mitigation: `core/` + `teachers-lab/` + a committed `web/out` keep a Python-only path.
2. `next-intl` with `output: "export"` needs fully static locale routes; if it fights us, fall back to a small custom message loader (about 60 lines).
3. Base UI is newer than Radix and has fewer copy-paste examples; we hand-write the components, which costs time but not risk of a blocked registry.
4. Two languages to maintain (Python and TypeScript). Mitigation: the generated types and the contract test; no business logic in TypeScript.
5. Scope: this is a rebuild of the front end, not a restyle. Phases 3-6 are most of the effort.
6. Dataset realism (clean, near-separable): not an engineering risk but a presentation risk; section 5 item 2.
7. Single global SQLite file: fine for a coursework demo, not multi-user. Out of scope unless asked.

## 12. Decisions (answered by Lucas, Oct 20)

1. One-process delivery (FastAPI serving a static Next build): **yes**.
2. Repo split `core/ api/ web/ teachers-lab/`, history kept: **yes**.
3. Ranking by Naive Bayes probability, profile similarity shown separately: **yes**.
4. N, P, K shown without units until the source unit is confirmed: **yes**.
5. Marathi review: **farmers** review the wording; crop names use the names farmers actually say (for example the field crop rice is भात, chickpea is हरभरा). Draft names live in `utils/i18n.py` (`CROP_MR`) and are marked unreviewed.
6. A Node-built front end is acceptable: **yes**, so `web/out` ships in the release zip as a primary deliverable (a Python-only run still works through `teachers-lab/`).

Still open: Hretz's confirmation of 6 from the teacher's side (Lucas answered on her behalf), and the exact source unit of N, P, K.
- **Phase 7d (done, Oct 21): the pages the professor will demo.** Lucas said "you pick": the five headline algorithms, in this order: ID3, Naive Bayes, K-Means, Apriori, Hierarchical. Each is a function in `core/teachers.py` (plain data, no Streamlit), a route under `/api/teachers/`, and a page under `web/app/[lang]/teachers/`, in English and Marathi, with editable readings where the page is about a check, a phone layout, and tests that compare every number on the page with the API. Found on the way: the shared progress bar sent `aria-valuenow` in exponent form for tiny values (fixed in `Track`, so every bar is covered). Not ported (not needed for the demo): FP-Growth and Eclat, Water Lab, What-if Lab, Data Insights, Data Lake, Data Prep; they stay in `teachers-lab/`.
- **Mobile (Oct 21):** below 768 px the sidebar is a header with one scrolling row of tabs and a "Current check" toggle; grids stack, tables scroll in their own box, tap targets are at least 34 px, inputs are 16 px. A test walks every page x language x 8 window sizes x scroll positions.
- **Phase 8 (done, Oct 21): cut-over.** The lab's own Home, What should I grow?, Crop Doctor and Plan B are deleted (`teachers-lab/pages/14-16` and the dashboard in `app.py`); the lab opens on its For teachers page, which lists every technical page, and has one sidebar link. A real-browser test opens the lab and checks that the old addresses give "Page not found". `make release` builds the site and `tools/make_release.py` packs `dist/agrimine-release.zip` from the committed files plus the prebuilt `web/out` (Python only to run). The README and demo script were rewritten for the web app. Clean-machine run (Oct 21): the zip unpacked into a new folder, a new virtualenv, `pip install -r requirements.txt`, then `python -m api` with no Node or npm on the PATH. Result: health ok; all 12 web pages answered 200; a saved check predicted Rice at 0.997; the lab started by itself (`/api/lab` available, Streamlit health ok) and stopped when the API stopped; the teacher routes gave ID3 accuracy 0.902 and 821 Apriori rules; Home in a real browser showed the same numbers as the development build. Still open: the farmers' review of the Marathi text and the crop drawings (needs people, not code).


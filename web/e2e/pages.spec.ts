import { expect, test, type Page } from "@playwright/test";

/**
 * What should I grow?, Crop Doctor, Plan B and For teachers, against the real API. Serial and ordered like home.spec.ts:
 * the database starts empty, so the first tests see "nothing saved", then a check is created through the API.
 */
test.describe.configure({ mode: "serial" });

const RICE = { N: 90, P: 42, K: 43, temperature: 20.9, humidity: 82, ph: 6.5, rainfall: 202.9 };
const NOON = new Date("2026-10-20T10:00:00");

async function open(page: Page, path: string, theme: "light" | "dark" = "light") {
  await page.clock.setFixedTime(NOON);
  await page.addInitScript((t) => { if (!localStorage.getItem("theme")) localStorage.setItem("theme", t); }, theme);
  await page.goto(path);
  await page.evaluate(() => document.fonts.ready);
}
/** The sidebar fills in by itself (current check, recent checks, the Crop Doctor chip), after the page content: wait for it too. */
const sidebarReady = async (page: Page) => {
  if (!page.url().includes("check=")) return;
  await expect(page.getByTestId("current-check")).toBeVisible();
  await expect(page.getByTestId("recent-checks")).toBeVisible();
  await expect(page.getByRole("navigation").getByRole("link").nth(2)).toContainText(/Good|Moderate|Needs attention|चांगले|मध्यम|लक्ष द्यावे/);   // the third link is Crop Doctor in either language; its chip has loaded
};
const settled = async (page: Page) => {
  await sidebarReady(page);
  await expect(page.getByRole("status").filter({ hasText: "Loading" })).toHaveCount(0, { timeout: 15_000 });
  await page.waitForTimeout(400); // the 300 ms debounce and the opacity transition
};
const shot = (page: Page, name: string) => expect(page).toHaveScreenshot(name, { fullPage: true, mask: [page.getByTestId("date")] });
const reading = (page: Page, key: string) => page.locator(`#reading-${key}`);

test("with nothing saved, every page starts from the dataset's typical values and still answers", async ({ page, request }) => {
  const meta = await (await request.get("/api/meta")).json();
  for (const path of ["/en/grow/", "/en/doctor/", "/en/plan-b/"]) {
    await open(page, path);
    await expect(page.getByTestId("readings")).toContainText("typical values");
    for (const f of meta.features) await expect(reading(page, f.key)).toHaveValue(String(f.default));
  }
  await page.setViewportSize({ width: 1536, height: 1024 });
  await open(page, "/en/grow/");
  await settled(page);
  await expect(page.getByTestId("recommended")).toBeVisible(); // a result even though no check exists
  await expect(page.getByTestId("grow-best")).not.toBeEmpty();
});

test("the sidebar chip is absent while nothing is saved", async ({ page }) => {
  await open(page, "/en/");
  await expect(page.getByRole("link", { name: /Crop Doctor/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /Crop Doctor/ })).not.toContainText("Good");
});

test("seed one check through the API", async ({ request }) => {
  const made = await request.post("/api/checks", { data: RICE });
  expect(made.status()).toBe(201);
});

test("What should I grow? shows the API's recommendation and ranking for the check", async ({ page, request }) => {
  await page.setViewportSize({ width: 1536, height: 1024 });
  await open(page, "/en/grow/?check=1");
  await settled(page);
  const rec = await (await request.post("/api/recommend", { data: RICE })).json();
  await expect(page.getByTestId("readings")).toContainText("check #1");
  await expect(reading(page, "rainfall")).toHaveValue("202.9");
  await expect(page.getByTestId("grow-best")).toContainText("Rice");
  await expect(page.getByTestId("grow-probability")).toHaveText(`${(rec.probability * 100).toFixed(1)}%`);
  await expect(page.getByTestId("tree")).toContainText("Agrees");
  await expect(page.getByTestId("match")).toContainText(`${Math.round(rec.ranking[0].match)}`);
  const rows = page.getByTestId("ranking").getByRole("listitem");
  await expect(rows).toHaveCount(8);
  await expect(rows.nth(0)).toContainText("Rice");
  await expect(rows.nth(1)).toContainText(rec.ranking[1].crop.label);
  await page.getByRole("button", { name: "Show all 22 crops" }).click();
  await expect(rows).toHaveCount(22);
  await expect(page.getByTestId("why")).toContainText("Why Rice?");
  await expect(page.getByTestId("why").getByText("Inside the usual range").first()).toBeVisible();
});

test("editing a reading re-asks the API and Reset brings the check back (nothing is saved)", async ({ page, request }) => {
  await open(page, "/en/grow/?check=1");
  await settled(page);
  await expect(page.getByTestId("grow-best")).toContainText("Rice");
  await reading(page, "rainfall").fill("40");
  for (const [k, v] of Object.entries({ humidity: "30", temperature: "28", N: "30", K: "20" })) await reading(page, k).fill(v);
  await expect(page.getByTestId("readings")).toContainText("Edited");
  await expect(page.getByTestId("grow-best")).not.toContainText("Rice", { timeout: 10_000 });
  expect((await (await request.get("/api/meta")).json()).saved_checks).toBe(1); // still exactly the one check
  await page.getByRole("button", { name: "Reset" }).click();
  await expect(reading(page, "rainfall")).toHaveValue("202.9");
  await expect(page.getByTestId("grow-best")).toContainText("Rice", { timeout: 10_000 });
});

test("an invalid reading is marked, no result is shown for it, and fixing it brings the result back", async ({ page }) => {
  await open(page, "/en/grow/?check=1");
  await settled(page);
  await reading(page, "ph").fill("99");
  await expect(reading(page, "ph")).toHaveAttribute("aria-invalid", "true");
  await expect(page.getByText("Fix the marked readings to see the result.")).toBeVisible();
  await expect(page.getByTestId("recommended")).toHaveCount(0);
  await reading(page, "ph").fill("6.5");
  await expect(page.getByTestId("recommended")).toBeVisible();
});

test("compare: add and remove crops, ranges match Crop Doctor, at most 4", async ({ page, request }) => {
  await open(page, "/en/grow/?check=1");
  await settled(page);
  const table = page.getByTestId("compare");
  await expect(table.getByRole("columnheader")).toHaveCount(2 + 3); // blank, your field, and the three most likely crops
  for (const name of ["Rice", "Jute", "Coffee"]) await expect(table.getByRole("columnheader", { name })).toBeVisible();
  await table.getByRole("combobox", { name: "Add a crop" }).click();
  await expect(page.getByRole("option", { name: "Coffee" })).toHaveCount(0); // already compared: not offered again
  await page.getByRole("option", { name: "Papaya" }).click();
  await expect(table.getByRole("columnheader", { name: "Papaya" })).toBeVisible();
  const doc = await (await request.post("/api/doctor", { data: { values: RICE, crop: "papaya" } })).json();
  const p = doc.readings.find((r: { feature: string }) => r.feature === "P");
  await expect(table.getByRole("row", { name: /Phosphorus/ })).toContainText(`${Math.round(p.low)}–${Math.round(p.high)}`);
  await expect(table.getByText("Up to 4 crops")).toBeVisible();
  await expect(table.getByRole("combobox", { name: "Add a crop" })).toHaveCount(0); // the limit hides the add control
  await table.getByRole("button", { name: "Remove Papaya" }).click();
  await expect(table.getByRole("columnheader", { name: "Papaya" })).toHaveCount(0);
  await expect(table.getByRole("combobox", { name: "Add a crop" })).toBeVisible();
  // the last crop cannot be removed: a comparison of nothing is not a comparison
  await table.getByRole("button", { name: "Remove Jute" }).click();
  await table.getByRole("button", { name: "Remove Coffee" }).click();
  await expect(table.getByRole("button", { name: "Remove Rice" })).toBeDisabled();
});

test("Crop Doctor: the recommended crop is chosen first, a poor fit shows what to do about each reading", async ({ page, request }) => {
  await page.setViewportSize({ width: 1536, height: 1024 });
  await open(page, "/en/doctor/?check=1");
  await settled(page);
  await expect(page.getByTestId("overall")).toContainText("Rice");
  await expect(page.getByTestId("overall")).toContainText("Good");
  await expect(page.getByTestId("tips")).toContainText("Nothing to change");
  await page.getByRole("combobox", { name: "Crop you want to grow" }).click();
  await page.getByRole("option", { name: /Coffee/ }).click();
  await settled(page);
  const doc = await (await request.post("/api/doctor", { data: { values: RICE, crop: "coffee" } })).json();
  await expect(page.getByTestId("score")).toHaveText(`${Math.round(doc.score * 100)}%`);
  await expect(page.getByTestId("overall")).toContainText("Needs attention");
  await expect(page.getByTestId("row-P")).toContainText("Needs attention");
  await expect(page.getByTestId("row-N")).toContainText("Good");
  const tips = page.getByTestId("tips").getByRole("listitem");
  await expect(tips).toHaveCount(doc.needs_attention);
  await expect(tips.filter({ hasText: "Phosphorus" })).toContainText("no phosphate needed");
  await expect(page.getByRole("link", { name: /See crops that fit better/ })).toHaveAttribute("href", /\/en\/plan-b\/\?check=1$/);
});

test("Crop Doctor in Marathi: tips, crop names and statuses are all Marathi", async ({ page }) => {
  await open(page, "/mr/doctor/?check=1");
  await settled(page);
  await page.getByRole("combobox", { name: "तुम्हाला पिकवायचे पीक" }).click();
  await page.getByRole("option", { name: /कॉफी/ }).click();
  await settled(page);
  await expect(page.getByTestId("tips")).toContainText("स्फुरद जास्त आहे");
  await expect(page.getByTestId("row-P")).toContainText("लक्ष द्यावे");
  await expect(page.getByTestId("tips")).not.toContainText("Phosphorus is high");
});

test("Plan B: a weak choice gets a warning and better crops; a good choice gets a confirmation", async ({ page, request }) => {
  await page.setViewportSize({ width: 1536, height: 1024 });
  await open(page, "/en/plan-b/?check=1");
  await settled(page);
  await expect(page.getByTestId("verdict")).toHaveAttribute("data-level", "good"); // starts from the recommended crop
  await page.getByRole("combobox", { name: "Crop you would like to grow" }).click();
  await page.getByRole("option", { name: "Cotton" }).click();
  await settled(page);
  const plan = await (await request.post("/api/plan-b", { data: { values: RICE, preferred: "cotton" } })).json();
  await expect(page.getByTestId("verdict")).toHaveAttribute("data-level", "low");
  await expect(page.getByTestId("verdict")).toContainText("Cotton is a weaker fit");
  for (const a of plan.alternatives) await expect(page.getByTestId(`alt-${a.crop.key}`)).toContainText(a.crop.label);
  const rice = page.getByTestId("alt-rice");                       // rice is the closest crop to this field
  await expect(rice).toContainText("What it needs");
  await expect(rice).toContainText("7 of 7 readings fit");
  await expect(rice).toContainText("20.9–26.5 °C");                // the unit once, at the end, not on both ends
  await expect(rice).not.toContainText("20.9 °C–26.5 °C");
  await expect(page.getByTestId("planb-compare").getByRole("columnheader")).toHaveCount(2 + 4);
});

test("For teachers lists the algorithms and the measured accuracy", async ({ page, request }) => {
  await open(page, "/en/teachers/");
  await settled(page);
  await expect(page.getByTestId("algos").getByRole("listitem")).toHaveCount(8);
  const acc = await (await request.get("/api/insights/accuracy")).json();
  await expect(page.getByTestId("accuracy")).toContainText(`${(acc.models[0].accuracy * 100).toFixed(1)}%`);
});

const LAB_PAGES = { id3: "crop-advisor", nb: "model-council", kmeans: "cluster-explorer", hier: "hierarchical", apriori: "pattern-mining", fp: "fp-growth-and-eclat", regression: "water-lab" };

test("For teachers says so plainly when the lab is not running: no link that goes nowhere", async ({ page, request }) => {
  expect((await (await request.get("/api/lab")).json()).available).toBe(false);          // this test server runs with AGRIMINE_LAB=0
  await open(page, "/en/teachers/?check=1");
  await settled(page);
  await expect(page.getByTestId("lab-off")).toContainText("python -m api");
  for (const algo of Object.keys(LAB_PAGES)) {
    const item = page.getByTestId(`lab-${algo}`);
    await expect(item, algo).toHaveAttribute("aria-disabled", "true");
    await expect(item).not.toHaveAttribute("href", /.*/);
  }
  await expect(page.getByTestId("lab-home")).toHaveCount(0);
});

test("For teachers opens the lab on the same check, on the address the API reports", async ({ page }) => {
  await page.route("**/api/lab", (route) => route.fulfill({ json: { available: true, url: "http://lab.example:9999", note: "test" } }));
  await open(page, "/en/teachers/?check=1");
  await settled(page);
  for (const [algo, slug] of Object.entries(LAB_PAGES)) {
    const link = page.getByTestId(`lab-${algo}`);
    await expect(link, algo).toHaveAttribute("href", `http://lab.example:9999/${slug}?check=1`);
    await expect(link).toHaveAttribute("target", "_blank");
  }
  await expect(page.getByTestId("lab-match")).toHaveCount(0);                      // profile match has no lab page: no dead link
  await expect(page.getByTestId("lab-home")).toHaveAttribute("href", "http://lab.example:9999?check=1");
  await expect(page.getByTestId("lab-off")).toHaveCount(0);
});

test("the ID3 page shows exactly what the API says for the check: answer, steps, accuracy, alternatives", async ({ page, request }) => {
  await page.setViewportSize({ width: 1536, height: 1024 });
  await open(page, "/en/teachers/id3/?check=1");
  await settled(page);
  const api = await (await request.post("/api/teachers/id3", { data: RICE })).json();
  await expect(page.getByTestId("id3-crop")).toHaveText(api.crop.label);
  await expect(page.getByTestId("id3-purity")).toHaveText(`${(api.purity * 100).toFixed(1)}%`);
  await expect(page.getByTestId("id3-accuracy-value")).toHaveText(`${(api.accuracy * 100).toFixed(1)}%`);
  await expect(page.getByTestId("id3-accuracy")).toContainText(`${api.n_train.toLocaleString("en")} rows`);
  const steps = page.getByTestId("id3-step");
  await expect(steps).toHaveCount(api.path.length);
  for (let i = 0; i < api.path.length; i++) {                       // each step: the feature, the bin and the rows, in the API's order
    const text = await steps.nth(i).innerText();
    expect(text, `step ${i + 1}`).toContain(String(Number(api.path[i].value.toFixed(2))));
    expect(text).toContain(api.path[i].rows_here.toLocaleString("en"));
    expect(text).toContain(api.path[i].gain.toFixed(3));
  }
  await expect(page.getByTestId("id3-end")).toContainText(api.crop.label);
  for (const a of api.alternatives) await expect(page.getByTestId("id3-alts")).toContainText(a.crop.label);
  await expect(page.getByTestId("id3-model")).toContainText(`${api.model.leaves} final nodes`);
});

test("editing a reading on the ID3 page re-runs the tree for those values (and saves nothing)", async ({ page, request }) => {
  const before = (await (await request.get("/api/meta")).json()).saved_checks;
  await page.setViewportSize({ width: 1536, height: 1024 });
  await open(page, "/en/teachers/id3/?check=1");
  await settled(page);
  const edited = { ...RICE, N: 20, rainfall: 40, humidity: 25 };
  for (const [key, value] of Object.entries(edited)) await reading(page, key).fill(String(value));
  const api = await (await request.post("/api/teachers/id3", { data: edited })).json();
  await expect(page.getByTestId("id3-crop")).toHaveText(api.crop.label, { timeout: 10_000 });
  await expect(page.getByTestId("id3-step")).toHaveCount(api.path.length);
  await expect(page.getByTestId("id3-purity")).toHaveText(`${(api.purity * 100).toFixed(1)}%`);
  expect((await (await request.get("/api/meta")).json()).saved_checks).toBe(before);
});

test("the ID3 page in Marathi: Marathi crop and bin names, Latin digits, the same numbers", async ({ page, request }) => {
  await page.setViewportSize({ width: 1536, height: 1024 });
  await open(page, "/mr/teachers/id3/?check=1", "dark");
  await settled(page);
  const api = await (await request.post("/api/teachers/id3", { data: RICE })).json();
  await expect(page.getByTestId("id3-crop")).toHaveText(api.crop.label_mr);
  await expect(page.getByTestId("id3-path")).toContainText(/खूप कमी|कमी|मध्यम|जास्त|खूप जास्त/);
  const body = await page.getByTestId("id3-path").innerText();
  expect(body).not.toMatch(/[\u0966-\u096F]/);                                   // no Devanagari digits anywhere in the path
  await expect(page.getByTestId("id3-accuracy-value")).toHaveText(`${(api.accuracy * 100).toFixed(1)}%`);
});

test("For teachers links to the ported ID3 page on the same check, and the page links back", async ({ page }) => {
  await open(page, "/en/teachers/?check=1");
  await settled(page);
  await expect(page.getByTestId("web-id3")).toHaveAttribute("href", "/en/teachers/id3/?check=1");
  await expect(page.getByTestId("web-fp")).toHaveCount(0);                    // not ported yet: no link to a page that does not exist
  await page.getByTestId("web-id3").click();
  await expect(page).toHaveURL(/\/en\/teachers\/id3\/\?check=1$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("ID3 decision tree");
  await expect(page.getByRole("navigation").getByRole("link", { name: /For teachers/ })).toHaveAttribute("aria-current", "page");
  await page.getByRole("link", { name: "For teachers" }).filter({ hasNot: page.getByRole("navigation") }).first().click();
  await expect(page).toHaveURL(/\/en\/teachers\/\?check=1$|\/en\/teachers\/$/);
});

for (const [theme, lang] of [["light", "en"], ["dark", "mr"]] as const) {
  test(`ID3 page looks the same: ${theme} ${lang}`, async ({ page }) => {
    await page.setViewportSize({ width: 1536, height: 1024 });
    await open(page, `/${lang}/teachers/id3/?check=1`, theme);
    await settled(page);
    await shot(page, `id3-${theme}-${lang}-1536x1024.png`);
  });
}

test("the Naive Bayes page shows exactly what the API says: both answers, the six probabilities, why, the worked formula, per-crop accuracy", async ({ page, request }) => {
  await page.setViewportSize({ width: 1536, height: 1024 });
  await open(page, "/en/teachers/naive-bayes/?check=1");
  await settled(page);
  const api = await (await request.post("/api/teachers/naive-bayes", { data: RICE })).json();
  await expect(page.getByTestId("nb-agree")).toHaveText(api.agree ? "The models agree" : "The models disagree");
  await expect(page.getByTestId("nb-id3-crop")).toHaveText(api.id3.crop.label);
  await expect(page.getByTestId("nb-nb-crop")).toHaveText(api.nb.crop.label);
  await expect(page.getByTestId("nb-prob")).toHaveText(`${(api.nb.probability * 100).toFixed(1)}%`);
  await expect(page.getByTestId("nb-purity")).toHaveText(`${(api.id3.purity * 100).toFixed(1)}%`);
  await expect(page.getByTestId("nb-nb-acc")).toHaveText(`${(api.nb.accuracy * 100).toFixed(1)}%`);
  await expect(page.getByTestId("nb-id3-acc")).toHaveText(`${(api.id3.accuracy * 100).toFixed(1)}%`);
  const top = page.getByTestId("nb-top").getByRole("listitem");
  await expect(top).toHaveCount(6);
  await expect(top.first()).toContainText(api.top[0].crop.label);
  await expect(page.getByTestId("nb-why-row")).toHaveCount(8);                      // seven readings + the crop's frequency
  await expect(page.getByTestId("nb-why-total")).toContainText(`${api.why_total > 0 ? "+" : ""}${api.why_total.toFixed(2)}`);
  const rows = page.getByTestId("nb-worked-row");
  await expect(rows).toHaveCount(7);
  for (let i = 0; i < 7; i++) await expect(rows.nth(i)).toContainText(String(Number(api.worked.features[i].log_likelihood.toFixed(2))));
  await expect(page.getByTestId("nb-worked-steps")).toContainText(String(Number(api.worked.joint.toFixed(2))));
  await expect(page.getByTestId("nb-worked-steps")).toContainText(`${(api.nb.probability * 100).toFixed(1)}%`);
  await expect(page.getByTestId("nb-percrop-row")).toHaveCount(22);
});

test("editing a reading on the Naive Bayes page re-runs both models for those values (and saves nothing)", async ({ page, request }) => {
  const before = (await (await request.get("/api/meta")).json()).saved_checks;
  await page.setViewportSize({ width: 1536, height: 1024 });
  await open(page, "/en/teachers/naive-bayes/?check=1");
  await settled(page);
  const edited = { ...RICE, N: 20, rainfall: 40, humidity: 25 };
  for (const [key, value] of Object.entries(edited)) await reading(page, key).fill(String(value));
  const api = await (await request.post("/api/teachers/naive-bayes", { data: edited })).json();
  await expect(page.getByTestId("nb-nb-crop")).toHaveText(api.nb.crop.label, { timeout: 10_000 });
  await expect(page.getByTestId("nb-id3-crop")).toHaveText(api.id3.crop.label);
  await expect(page.getByTestId("nb-prob")).toHaveText(`${(api.nb.probability * 100).toFixed(1)}%`);
  await expect(page.getByTestId("nb-agree")).toHaveText(api.agree ? "The models agree" : "The models disagree");
  if (!api.agree) await expect(page.getByTestId("nb-disagree-note")).toContainText(api.id3.crop.label);
  expect((await (await request.get("/api/meta")).json()).saved_checks).toBe(before);
});

test("the Naive Bayes page in Marathi: Marathi crop and reading names, Latin digits", async ({ page, request }) => {
  await page.setViewportSize({ width: 1536, height: 1024 });
  await open(page, "/mr/teachers/naive-bayes/?check=1", "dark");
  await settled(page);
  const api = await (await request.post("/api/teachers/naive-bayes", { data: RICE })).json();
  await expect(page.getByTestId("nb-nb-crop")).toHaveText(api.nb.crop.label_mr);
  await expect(page.getByTestId("nb-agree")).toHaveText("दोन्ही सहमत आहेत");
  const body = await page.getByTestId("nb-worked").innerText();
  expect(body).not.toMatch(/[\u0966-\u096F]/);
  await expect(page.getByTestId("nb-prob")).toHaveText(`${(api.nb.probability * 100).toFixed(1)}%`);
});

test("For teachers links to the Naive Bayes page on the same check", async ({ page }) => {
  await open(page, "/en/teachers/?check=1");
  await settled(page);
  await expect(page.getByTestId("web-nb")).toHaveAttribute("href", "/en/teachers/naive-bayes/?check=1");
  await expect(page.getByTestId("web-fp")).toHaveCount(0);
  await page.getByTestId("web-nb").click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Naive Bayes and ID3");
});

for (const [theme, lang] of [["light", "en"], ["dark", "mr"]] as const) {
  test(`Naive Bayes page looks the same: ${theme} ${lang}`, async ({ page }) => {
    await page.setViewportSize({ width: 1536, height: 1024 });
    await open(page, `/${lang}/teachers/naive-bayes/?check=1`, theme);
    await settled(page);
    await shot(page, `nb-${theme}-${lang}-1536x1024.png`);
  });
}

test("the K-Means page shows exactly what the API says for k = 4: group, numbers, profiles, crops, elbow", async ({ page, request }) => {
  await page.setViewportSize({ width: 1536, height: 1024 });
  await open(page, "/en/teachers/kmeans/?check=1");
  await settled(page);
  const api = await (await request.post("/api/teachers/kmeans?k=4", { data: RICE })).json();
  await expect(page.getByTestId("km-k")).toHaveText("4");
  await expect(page.getByTestId("km-inertia")).toHaveText(Math.round(api.inertia).toLocaleString("en"));
  await expect(page.getByTestId("km-sil")).toHaveText(api.silhouette.toFixed(3));
  await expect(page.getByTestId("km-var")).toHaveText(`${((api.variance[0] + api.variance[1]) * 100).toFixed(1)}%`);
  await expect(page.getByTestId("km-yours-text")).toHaveText(`Your readings are closest to group ${api.your_cluster + 1}.`);
  const rows = page.getByTestId("km-profile-row");
  await expect(rows).toHaveCount(4);
  for (let i = 0; i < 4; i++) {
    const g = api.clusters[i];
    await expect(rows.nth(i)).toContainText(g.records.toLocaleString("en"));
    await expect(rows.nth(i)).toContainText(g.top_crop.label);
    await expect(rows.nth(i)).toContainText(String(Number(g.averages.rainfall.toFixed(2))));
  }
  await expect(rows.nth(api.your_cluster)).toContainText("You");
  await expect(page.getByTestId("km-crop-row")).toHaveCount(22);
  await expect(page.getByTestId("km-map").locator("circle")).toHaveCount(2200 + 1);        // every record, and the ring around your own X
  await expect(page.getByTestId("km-choose-note")).toContainText(`k = ${api.best_k} here`);
});

test("moving the K-Means slider to 7 re-runs the clustering with 7 groups; editing a reading moves your group (and saves nothing)", async ({ page, request }) => {
  const before = (await (await request.get("/api/meta")).json()).saved_checks;
  await page.setViewportSize({ width: 1536, height: 1024 });
  await open(page, "/en/teachers/kmeans/?check=1");
  await settled(page);
  await page.getByTestId("km-slider").fill("7");
  const api7 = await (await request.post("/api/teachers/kmeans?k=7", { data: RICE })).json();
  await expect(page.getByTestId("km-profile-row")).toHaveCount(7, { timeout: 10_000 });
  await expect(page.getByTestId("km-k")).toHaveText("7");
  await expect(page.getByTestId("km-sil")).toHaveText(api7.silhouette.toFixed(3));
  await expect(page.getByTestId("km-inertia")).toHaveText(Math.round(api7.inertia).toLocaleString("en"));
  await expect(page.getByTestId("km-legend").getByRole("listitem")).toHaveCount(8);          // seven groups and "your field"
  const edited = { ...RICE, N: 20, rainfall: 40, humidity: 25, temperature: 35 };
  for (const [key, value] of Object.entries(edited)) await reading(page, key).fill(String(value));
  const api = await (await request.post("/api/teachers/kmeans?k=7", { data: edited })).json();
  await expect(page.getByTestId("km-yours-text")).toHaveText(`Your readings are closest to group ${api.your_cluster + 1}.`, { timeout: 10_000 });
  expect((await (await request.get("/api/meta")).json()).saved_checks).toBe(before);
});

test("the K-Means page in Marathi: Marathi names, Latin digits, the same numbers", async ({ page, request }) => {
  await page.setViewportSize({ width: 1536, height: 1024 });
  await open(page, "/mr/teachers/kmeans/?check=1", "dark");
  await settled(page);
  const api = await (await request.post("/api/teachers/kmeans?k=4", { data: RICE })).json();
  await expect(page.getByTestId("km-yours-text")).toContainText(`गट ${api.your_cluster + 1}`);
  await expect(page.getByTestId("km-profile-row").first()).toContainText(api.clusters[0].top_crop.label_mr);
  expect(await page.getByTestId("km-profiles").innerText()).not.toMatch(/[\u0966-\u096F]/);
  await expect(page.getByTestId("km-sil")).toHaveText(api.silhouette.toFixed(3));
});

test("For teachers links to the K-Means page on the same check", async ({ page }) => {
  await open(page, "/en/teachers/?check=1");
  await settled(page);
  await expect(page.getByTestId("web-kmeans")).toHaveAttribute("href", "/en/teachers/kmeans/?check=1");
  await expect(page.getByTestId("web-fp")).toHaveCount(0);
  await page.getByTestId("web-kmeans").click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("K-Means clusters");
});

for (const [theme, lang] of [["light", "en"], ["dark", "mr"]] as const) {
  test(`K-Means page looks the same: ${theme} ${lang}`, async ({ page }) => {
    await page.setViewportSize({ width: 1536, height: 1024 });
    await open(page, `/${lang}/teachers/kmeans/?check=1`, theme);
    await settled(page);
    await shot(page, `km-${theme}-${lang}-1536x1024.png`);
  });
}

test("the Apriori page shows exactly what the API says at the default settings, and the sort headings work", async ({ page, request }) => {
  await page.setViewportSize({ width: 1536, height: 1024 });
  await open(page, "/en/teachers/apriori/?check=1");
  await settled(page);
  const api = await (await request.get("/api/teachers/apriori")).json();
  await expect(page.getByTestId("apr-itemsets")).toHaveText(api.itemsets.toLocaleString("en"));
  await expect(page.getByTestId("apr-rules")).toHaveText(api.rules_total.toLocaleString("en"));
  await expect(page.getByTestId("apr-time")).toHaveText(/^\d+\.\d\d s$/);
  const top = page.getByTestId("apr-top-rule");
  await expect(top).toHaveCount(3);
  await expect(top.first()).toContainText("Potassium high + Humidity low → Chickpea");     // the strongest rule, in words
  await expect(top.first()).toContainText(`lift ${api.rules[0].lift.toFixed(1)}`);
  await expect(page.getByTestId("apr-row")).toHaveCount(100);
  await expect(page.getByTestId("apr-shown")).toHaveText(`Showing the strongest 100 of ${api.rules_total} rules.`);
  await page.getByTestId("apr-sort-support").click();                                     // sort by support, highest first
  const supports = async () => (await page.getByTestId("apr-row").locator("td:nth-child(3)").allInnerTexts()).map(Number);
  const desc = await supports();
  expect(desc).toEqual([...desc].sort((a, b) => b - a));
  await page.getByTestId("apr-sort-support").click();                                     // again: lowest first
  const asc = await supports();
  expect(asc).toEqual([...asc].sort((a, b) => a - b));
  expect(asc[0]).toBeLessThanOrEqual(desc[0]);
});

test("changing the Apriori settings re-mines: stricter settings give the API's smaller count, a crop filter narrows the rules, none gives an empty state", async ({ page, request }) => {
  await page.setViewportSize({ width: 1536, height: 1024 });
  await open(page, "/en/teachers/apriori/?check=1");
  await settled(page);
  await page.getByTestId("apr-conf").fill("0.95");
  await page.getByTestId("apr-support").fill("0.03");
  const strict = await (await request.get("/api/teachers/apriori?min_confidence=0.95&min_support=0.03")).json();
  await expect(page.getByTestId("apr-rules")).toHaveText(strict.rules_total.toLocaleString("en"), { timeout: 10_000 });
  await expect(page.getByTestId("apr-itemsets")).toHaveText(strict.itemsets.toLocaleString("en"));
  await expect(page.getByTestId("apr-conf-v")).toHaveText("0.95");
  await page.getByTestId("apr-conf").fill("1");
  await page.getByTestId("apr-support").fill("0.1");
  await page.getByRole("button", { name: "2", exact: true }).click();                        // largest pattern: 2 items
  await expect(page.getByTestId("apr-none")).toBeVisible({ timeout: 10_000 });                 // nothing reaches 10% support and 100% confidence in pairs
  await page.getByTestId("apr-conf").fill("0.5");
  await page.getByTestId("apr-support").fill("0.01");
  await page.getByRole("button", { name: "5", exact: true }).click();
  await page.getByRole("combobox", { name: "Filter by crop" }).click();
  await page.getByRole("option", { name: "Rice" }).click();
  const rice = await (await request.get("/api/teachers/apriori?min_confidence=0.5&crop=rice")).json();
  await expect(page.getByTestId("apr-rules")).toHaveText(rice.rules_total.toLocaleString("en"), { timeout: 10_000 });
  await expect(page.getByTestId("apr-top-rule").first()).toContainText("Rice");
});

test("the Apriori page in Marathi: Marathi crop and level words, Latin digits, the same counts", async ({ page, request }) => {
  await page.setViewportSize({ width: 1536, height: 1024 });
  await open(page, "/mr/teachers/apriori/?check=1", "dark");
  await settled(page);
  const api = await (await request.get("/api/teachers/apriori")).json();
  await expect(page.getByTestId("apr-rules")).toHaveText(api.rules_total.toLocaleString("en"));
  await expect(page.getByTestId("apr-top-rule").first()).toContainText("हरभरा");               // chickpea
  expect(await page.getByTestId("apr-table").innerText()).not.toMatch(/[\u0966-\u096F]/);
});

test("For teachers links to the Apriori page", async ({ page }) => {
  await open(page, "/en/teachers/?check=1");
  await settled(page);
  await expect(page.getByTestId("web-apriori")).toHaveAttribute("href", "/en/teachers/apriori/?check=1");
  await page.getByTestId("web-apriori").click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Apriori patterns");
});

for (const [theme, lang] of [["light", "en"], ["dark", "mr"]] as const) {
  test(`Apriori page looks the same: ${theme} ${lang}`, async ({ page }) => {
    await page.setViewportSize({ width: 1536, height: 1024 });
    await open(page, `/${lang}/teachers/apriori/?check=1`, theme);
    await settled(page);
    await expect(page.getByTestId("apr-time")).toBeVisible();
    await expect(page).toHaveScreenshot(`apr-${theme}-${lang}-1536x1024.png`, { fullPage: true, mask: [page.getByTestId("date"), page.getByTestId("apr-time")] });   // the mining time is measured, so it differs every run
  });
}

test("the Hierarchical page shows exactly what the API says: numbers, the tree, the clusters, DIANA", async ({ page, request }) => {
  await page.setViewportSize({ width: 1536, height: 1024 });
  await open(page, "/en/teachers/hierarchical/?check=1");
  await settled(page);
  const api = await (await request.get("/api/teachers/hierarchical?method=ward&k=4")).json();
  await expect(page.getByTestId("hier-coph")).toHaveText(api.cophenetic.toFixed(3));
  await expect(page.getByTestId("hier-last")).toHaveText(api.last_height.toFixed(2));
  await expect(page.getByTestId("hier-crops")).toHaveText("22");
  await expect(page.getByTestId("hier-segment")).toHaveCount(21);
  const leaves = page.getByTestId("hier-leaf");
  await expect(leaves).toHaveCount(22);
  expect(await leaves.allTextContents()).toEqual(api.order.map((i: number) => api.crops[i].label));      // the crops along the bottom in the API's order
  const clusters = page.getByTestId("hier-cluster");
  await expect(clusters).toHaveCount(4);
  for (let c = 0; c < 4; c++) {
    await expect(clusters.nth(c)).toContainText(`${api.clusters[c].length} crops`);
    for (const crop of api.clusters[c]) await expect(clusters.nth(c)).toContainText(crop.label);
  }
  const rows = page.getByTestId("hier-diana-row");
  await expect(rows).toHaveCount(api.diana_steps.length);
  await expect(rows.first()).toContainText(api.diana_steps[0].splinter.map((c: { label: string }) => c.label).join(", "));
  await expect(page.getByTestId("hier-same")).toContainText(api.same ? "give the same clusters" : "give different clusters");
});

test("changing the linkage and k re-draws the tree and the clusters", async ({ page, request }) => {
  await page.setViewportSize({ width: 1536, height: 1024 });
  await open(page, "/en/teachers/hierarchical/?check=1");
  await settled(page);
  await page.getByRole("button", { name: "Single", exact: true }).click();
  await page.getByTestId("hier-slider").fill("6");
  const api = await (await request.get("/api/teachers/hierarchical?method=single&k=6")).json();
  await expect(page.getByTestId("hier-cluster")).toHaveCount(6, { timeout: 10_000 });
  await expect(page.getByTestId("hier-k")).toHaveText("6");
  await expect(page.getByTestId("hier-coph")).toHaveText(api.cophenetic.toFixed(3));
  await expect(page.getByTestId("hier-last")).toHaveText(api.last_height.toFixed(2));
  await expect(page.getByTestId("hier-method-help")).toContainText("closest pair");
  const rows = page.getByTestId("hier-diana-row");
  await expect(rows).toHaveCount(10);                                                               // k + 4 steps
  await expect(page.getByTestId("hier-same")).toContainText(`At k = 6, DIANA and Single linkage give ${api.same ? "the same" : "different"} clusters`);
  expect(await page.getByTestId("hier-leaf").allTextContents()).toEqual(api.order.map((i: number) => api.crops[i].label));
});

test("the Hierarchical page in Marathi: Marathi crop names and words, Latin digits, the same numbers", async ({ page, request }) => {
  await page.setViewportSize({ width: 1536, height: 1024 });
  await open(page, "/mr/teachers/hierarchical/?check=1", "dark");
  await settled(page);
  const api = await (await request.get("/api/teachers/hierarchical?method=ward&k=4")).json();
  expect(await page.getByTestId("hier-leaf").allTextContents()).toEqual(api.order.map((i: number) => api.crops[i].label_mr));
  await expect(page.getByTestId("hier-coph")).toHaveText(api.cophenetic.toFixed(3));
  await expect(page.getByTestId("hier-clusters")).toContainText("गट 1");
  expect(await page.getByTestId("hier-diana").innerText()).not.toMatch(/[\u0966-\u096F]/);
});

test("For teachers links to the Hierarchical page, and every ported algorithm has its page", async ({ page }) => {
  await open(page, "/en/teachers/?check=1");
  await settled(page);
  for (const [id, path] of [["id3", "id3"], ["nb", "naive-bayes"], ["kmeans", "kmeans"], ["apriori", "apriori"], ["hier", "hierarchical"]]) await expect(page.getByTestId(`web-${id}`)).toHaveAttribute("href", `/en/teachers/${path}/?check=1`);
  await page.getByTestId("web-hier").click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Hierarchical clustering");
});

for (const [theme, lang] of [["light", "en"], ["dark", "mr"]] as const) {
  test(`Hierarchical page looks the same: ${theme} ${lang}`, async ({ page }) => {
    await page.setViewportSize({ width: 1536, height: 1024 });
    await open(page, `/${lang}/teachers/hierarchical/?check=1`, theme);
    await settled(page);
    await shot(page, `hier-${theme}-${lang}-1536x1024.png`);
  });
}

test("every sidebar row has the same height, with or without a chip (a chip must not move the layout)", async ({ page }) => {
  await open(page, "/en/?check=1");
  await settled(page);
  const heights = await page.getByRole("navigation").getByRole("link").evaluateAll((els) => els.map((e) => Math.round(e.getBoundingClientRect().height * 10) / 10));
  expect(heights).toHaveLength(5);
  expect(new Set(heights).size, `row heights ${heights}`).toBe(1);
});

test("the sidebar chip shows the recommended crop's soil health and every link leads to a real page", async ({ page }) => {
  await open(page, "/en/?check=1");
  await settled(page);
  await expect(page.getByRole("link", { name: /Crop Doctor/ })).toContainText("Good");
  for (const [name, url, heading] of [["What should I grow?", /\/en\/grow\/\?check=1$/, "What should I grow?"], ["Crop Doctor", /\/en\/doctor\/\?check=1$/, "Crop Doctor"], ["Plan B", /\/en\/plan-b\/\?check=1$/, "Plan B"], ["For teachers", /\/en\/teachers\/\?check=1$/, "For teachers"]] as const) {
    await page.getByRole("navigation").getByRole("link", { name: new RegExp(name) }).click();
    await expect(page).toHaveURL(url);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(heading);
    await expect(page.getByRole("navigation").getByRole("link", { name: new RegExp(name) })).toHaveAttribute("aria-current", "page");
  }
});

for (const [route, theme, name] of [["grow", "light", "grow-light"], ["grow", "dark", "grow-dark"], ["doctor", "light", "doctor-light"], ["doctor", "dark", "doctor-dark"], ["plan-b", "light", "planb-light"], ["plan-b", "dark", "planb-dark"], ["teachers", "light", "teachers-light"]] as const) {
  test(`${route} looks the same: ${theme}`, async ({ page }) => {
    await page.setViewportSize({ width: 1536, height: 1024 });
    if (route === "teachers") await page.route("**/api/lab", (r) => r.fulfill({ json: { available: true, url: "http://127.0.0.1:8501", note: "test" } }));   // the normal state: the lab is running
    await open(page, `/en/${route}/?check=1`, theme);
    await settled(page);
    if (route === "teachers") await expect(page.getByTestId("lab-id3")).toHaveAttribute("href", /crop-advisor/);       // links have appeared before the picture
    await shot(page, `${name}-1536x1024.png`);
  });
}

test("teachers when the lab is not running looks the same", async ({ page }) => {
  await page.setViewportSize({ width: 1536, height: 1024 });
  await open(page, "/en/teachers/?check=1");
  await settled(page);
  await expect(page.getByTestId("lab-off")).toBeVisible();
  await shot(page, "teachers-lab-off-light-1536x1024.png");
});

test("Crop Doctor in Marathi with a poor fit looks the same (long Devanagari tips must not overflow)", async ({ page }) => {
  await page.setViewportSize({ width: 1536, height: 1024 });
  await open(page, "/mr/doctor/?check=1", "dark");
  await settled(page);
  await page.getByRole("combobox", { name: "तुम्हाला पिकवायचे पीक" }).click();
  await page.getByRole("option", { name: /कॉफी/ }).click();
  await settled(page);
  await expect(page.getByTestId("tips").getByRole("listitem")).toHaveCount(5);
  await shot(page, "doctor-mr-dark-coffee-1536x1024.png");
});

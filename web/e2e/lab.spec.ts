import { expect, test } from "@playwright/test";

/**
 * The whole chain, for real: `python -m api` starts the Streamlit lab next to itself (this group's server does), the web app's
 * For teachers page links to it with the current check, and the lab opens on that check. Nothing is faked here.
 * One shared database, so run the whole file.
 */
test.describe.configure({ mode: "serial" });

const RICE = { N: 90, P: 42, K: 43, temperature: 20.9, humidity: 82, ph: 6.5, rainfall: 202.9 };
const OTHER = { N: 20, P: 130, K: 200, temperature: 23, humidity: 92, ph: 6, rainfall: 110 };

test.beforeAll(async ({ request }) => {
  for (const values of [RICE, OTHER]) expect((await request.post("/api/checks", { data: values })).ok()).toBe(true);
  await expect.poll(async () => (await (await request.get("/api/lab")).json()).available, { timeout: 90_000, intervals: [500] }).toBe(true);
});

test("the API started the lab and reports where it is", async ({ request }) => {
  const lab = await (await request.get("/api/lab")).json();
  expect(lab.url).toBe("http://127.0.0.1:8177");
  expect(lab.note).toContain("started on port 8177");
  const health = await request.get("http://127.0.0.1:8177/_stcore/health");        // the lab itself, not through the API
  expect(await health.text()).toBe("ok");
});

for (const [check, firstValue] of [[1, "N 90"], [2, "N 20"]] as const) {
  test(`clicking "Open in the lab" for the ID3 tree opens the lab on check #${check} (no "page not found")`, async ({ page, context }) => {
    await page.goto(`/en/teachers/?check=${check}`);
    const link = page.getByTestId("lab-id3");
    await expect(link).toHaveAttribute("href", `http://127.0.0.1:8177/crop-advisor?check=${check}`);
    const popup = context.waitForEvent("page");
    await link.click();
    const lab = await popup;
    await expect(lab.getByText("Decision path for your input")).toBeVisible({ timeout: 60_000 });
    await expect(lab.getByText("Page not found")).toHaveCount(0);
    const side = lab.locator("[data-testid=stSidebar]");
    await expect(side).toContainText(`#${check}`);
    await expect(side).toContainText(firstValue);
    await expect(lab.getByText("ID3 recommends")).toBeVisible();
  });
}

test("another algorithm's link (Naive Bayes) opens the Model Council on the same check", async ({ page, context }) => {
  await page.goto("/en/teachers/?check=2");
  const popup = context.waitForEvent("page");
  await page.getByTestId("lab-nb").click();
  const lab = await popup;
  await expect(lab.locator("[data-testid=stSidebar]")).toContainText("#2", { timeout: 60_000 });
  await expect(lab.getByText("Page not found")).toHaveCount(0);
  await expect(lab.locator("[data-testid=stMain]")).toContainText("Model Council");              // this page, not the lab home
});

test("with no ?check= the lab shows the newest check, like the web app does", async ({ page, context }) => {
  await page.goto("/en/teachers/");
  const popup = context.waitForEvent("page");
  await page.getByTestId("lab-hier").click();
  const lab = await popup;
  await expect(lab.locator("[data-testid=stSidebar]")).toContainText("#2", { timeout: 60_000 });
});

test("the lab's front door is the For teachers page: one sidebar link, every technical page listed, and no copies of the farmer pages", async ({ page, context }) => {
  await page.goto("/en/teachers/?check=1");
  await expect(page.getByTestId("lab-home")).toHaveAttribute("href", "http://127.0.0.1:8177?check=1");
  const popup = context.waitForEvent("page");
  await page.getByTestId("lab-home").click();                       // "Open the technical lab", as a teacher would
  const lab = await popup;
  const main = lab.locator("[data-testid=stMain]");
  await expect(main).toContainText("Algorithms and where to find them", { timeout: 60_000 });
  for (const title of ["Crop Advisor", "Model Council", "Cluster Explorer", "Hierarchical", "Pattern Mining", "FP-Growth and Eclat", "Water Lab", "Data Insights", "Data Lake", "Data Prep", "What-if Lab", "Soil Analysis"]) await expect(main).toContainText(title);
  const side = lab.locator("[data-testid=stSidebar]");
  await expect(side.locator("a")).toHaveCount(await side.locator("a").count());          // (settled)
  const links = (await side.locator("a").allInnerTexts()).map((t) => t.trim()).filter(Boolean);
  expect(links.join(" | ")).toContain("For teachers");
  for (const gone of ["Home", "What should I grow?", "Crop Doctor", "Plan B"]) expect(links, `the lab has no "${gone}" link any more`).not.toContain(gone);
  for (const path of ["what-should-i-grow", "crop-doctor", "plan-b"]) {                     // the old pages really are gone, not just unlinked
    await lab.goto(`http://127.0.0.1:8177/${path}`);
    await expect(lab.getByText("Page not found")).toBeVisible({ timeout: 30_000 });
  }
});

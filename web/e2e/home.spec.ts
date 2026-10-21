import { expect, test, type Page } from "@playwright/test";

/**
 * Home on real data, against the real API (a fresh database each run). These tests share one database, so they run IN ORDER:
 * the first sees "no check yet", the next creates a check through the form, the rest look at what that check produced.
 */
test.describe.configure({ mode: "serial" });

const RICE = { N: "90", P: "42", K: "43", temperature: "20.9", humidity: "82", ph: "6.5", rainfall: "202.9" };
const NOON = new Date("2026-10-20T10:00:00"); // the greeting depends on the hour: freeze it so screenshots are stable

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
  await expect(page.getByRole("status")).toHaveCount(0, { timeout: 15_000 }); // every card has left its loading state
  await page.waitForTimeout(250);
};
const shot = (page: Page, name: string) =>
  expect(page).toHaveScreenshot(name, { fullPage: true, mask: [page.locator('[data-testid="date"]:visible')] }); // dates are the one thing that changes by the day

test("with nothing saved, Home says so and offers the way forward", async ({ page }) => {
  await page.setViewportSize({ width: 1536, height: 1024 });
  await open(page, "/en/");
  await expect(page.getByTestId("hero")).toHaveCount(0);
  await expect(page.getByText("Do a soil check to see the best crop for your field.")).toBeVisible();
  await expect(page.getByTestId("no-check")).toHaveCount(3); // Top 3, Plan B and Crop Doctor each explain instead of spinning forever
  await expect(page.getByTestId("stats")).toContainText("2,200");
  await expect(page.getByTestId("stats")).toContainText("none saved yet");
  await expect(page.getByTestId("farms")).toBeVisible(); // charts that do not need a check still work
  await settled(page);
  await shot(page, "home-empty-light-1536x1024.png");
});

test("a bad reading is refused next to its field and nothing is saved", async ({ page }) => {
  await open(page, "/en/check/");
  await expect(page.getByTestId("check-form")).toBeVisible();
  for (const [key, value] of Object.entries({ ...RICE, N: "999" })) await page.locator(`#field-${key}`).fill(value);
  await page.getByRole("button", { name: "Save and see the result" }).click();
  await expect(page.locator("#field-N")).toHaveAttribute("aria-invalid", "true");
  await expect(page.locator("#field-N-hint")).toContainText("Must be between 0 and 140");
  await expect(page.getByText("Please check the marked readings.")).toBeVisible();
  await expect(page).toHaveURL(/\/en\/check\/$/);
  expect((await (await page.request.get("/api/meta")).json()).saved_checks).toBe(0);
});

test("saving a check goes to Home, which shows what the API predicted", async ({ page }) => {
  await page.setViewportSize({ width: 1536, height: 1024 });
  await open(page, "/en/check/");
  for (const [key, value] of Object.entries(RICE)) await page.locator(`#field-${key}`).fill(value);
  await page.getByRole("button", { name: "Save and see the result" }).click();
  await expect(page).toHaveURL(/\/en\/\?check=1$/);
  await settled(page);
  await expect(page.getByTestId("hero-crop")).toContainText("Rice");
  await expect(page.getByTestId("hero-probability")).toHaveText("99.7%");
  await expect(page.getByTestId("top3")).toContainText("Rice");
  await expect(page.getByTestId("top3")).toContainText("Best choice");
  await expect(page.getByTestId("current-check")).toContainText("#1");
  await expect(page.getByTestId("recent-checks")).toContainText("#1 · Rice");
  await expect(page.getByTestId("stats")).toContainText("Saved checks");
  expect((await (await page.request.get("/api/meta")).json()).saved_checks).toBe(1);
});

test("what Home shows equals what the API says (nothing typed in)", async ({ page, request }) => {
  await open(page, "/en/?check=1");
  await settled(page);
  const check = await (await request.get("/api/checks/1")).json();
  const rec = await (await request.post("/api/recommend", { data: check.values })).json();
  const patterns = await (await request.get("/api/insights/patterns?limit=3")).json();
  const accuracy = await (await request.get("/api/insights/accuracy")).json();
  await expect(page.getByTestId("hero-probability")).toHaveText(`${(rec.probability * 100).toFixed(1)}%`);
  const top3 = rec.ranking.slice(0, 3).map((r: { crop: { label: string } }) => r.crop.label);
  for (const name of top3) await expect(page.getByTestId("top3")).toContainText(name);
  const planB = rec.similar.slice(0, 3).map((r: { crop: { label: string } }) => r.crop.label);
  for (const name of planB) await expect(page.getByTestId("planb")).toContainText(name);
  await expect(page.getByText(`Apriori · ${patterns.total.toLocaleString("en")} rules`)).toBeVisible();
  for (const m of accuracy.models) await expect(page.getByTestId("accuracy")).toContainText(`${(m.accuracy * 100).toFixed(1)}%`);
});

test("Marathi Home shows Marathi crop names and navigation", async ({ page }) => {
  await open(page, "/mr/?check=1");
  await settled(page);
  await expect(page.locator("html")).toHaveAttribute("lang", "mr");
  await expect(page.getByTestId("hero-crop")).toContainText("भात");
  await expect(page.getByTestId("top3")).toContainText("ताग");
  await expect(page.getByRole("link", { name: "पीक डॉक्टर" })).toBeVisible();
  await expect(page.getByTestId("hero-crop")).not.toContainText("Rice");
});

test("an unreachable service shows a plain message and recovers on retry", async ({ page }) => {
  let fail = true;
  await page.route("**/api/insights/gain", (route) => (fail ? route.fulfill({ status: 500, json: { code: "boom", message: "x", field: null, errors: null } }) : route.continue()));
  await open(page, "/en/?check=1");
  const card = page.getByRole("alert").filter({ hasText: "Could not reach the AgriMine service" });
  await expect(card).toBeVisible();
  fail = false;
  await card.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByTestId("gain")).toBeVisible();
});

for (const size of [{ w: 1366, h: 768 }, { w: 1536, h: 1024 }]) {
  test(`the sidebar stays put while the page scrolls at ${size.w}x${size.h}`, async ({ page }) => {
    await page.setViewportSize({ width: size.w, height: size.h });
    await open(page, "/en/?check=1");
    await settled(page);
    const docHeight = await page.evaluate(() => document.documentElement.scrollHeight);
    expect(docHeight, "the page must be taller than the window or this test proves nothing").toBeGreaterThan(size.h + 100);
    for (const y of [Math.round((docHeight - size.h) / 2), docHeight]) {
      await page.evaluate((to) => window.scrollTo(0, to), y);
      await page.waitForTimeout(150);
      const side = await page.locator("aside").boundingBox();
      // within 1px: sizes are in rem, so the page height is fractional and the browser rounds the last scroll step
      expect(Math.abs(side!.y), `sidebar top after scrolling to ${y}`).toBeLessThanOrEqual(1);
      expect(Math.abs(side!.height - size.h), "sidebar fills the window").toBeLessThanOrEqual(1);
      const profile = await page.getByTestId("profile").boundingBox();                  // the profile bar is still on screen
      expect(profile!.y + profile!.height).toBeLessThanOrEqual(size.h);
      expect(profile!.y).toBeGreaterThan(0);
    }
  });
}

for (const size of [{ w: 1536, h: 1024 }, { w: 1920, h: 1080 }]) {
  test(`the six farmer cards fit one screen at ${size.w}x${size.h}`, async ({ page }) => {
    await page.setViewportSize({ width: size.w, height: size.h });
    await open(page, "/en/?check=1");
    await settled(page);
    for (const id of ["hero", "top3", "doctor", "planb", "farms", "needs"]) {
      const box = await page.getByTestId(id).boundingBox();
      expect(box, id).not.toBeNull();
      expect(box!.y + box!.height, `${id} must end inside the window`).toBeLessThanOrEqual(size.h);
    }
  });
}

for (const lang of ["en", "mr"]) {
  for (const w of [1280, 1366, 1536, 1920]) {
    test(`the hero's reading chips show their whole label: ${lang} at ${w}px`, async ({ page }) => {
      await page.setViewportSize({ width: w, height: 900 });
      await open(page, `/${lang}/?check=1`);
      await settled(page);
      const chips = page.getByTestId("hero-mini");
      await expect(chips).toHaveCount(3);
      for (let i = 0; i < 3; i++) {
        const chip = chips.nth(i);
        const clipped = await chip.evaluate((el) => {
          const box = el.getBoundingClientRect();
          return [...el.querySelectorAll("*")].filter((n) => n.getBoundingClientRect().right > box.right + 0.5 || n.scrollWidth > n.clientWidth + 1).length;
        });
        expect(clipped, `chip ${i} (${await chip.innerText()})`).toBe(0);
      }
    });
  }
}

for (const [theme, lang, name] of [["light", "en", "home-light-en-1536x1024.png"], ["dark", "en", "home-dark-en-1536x1024.png"], ["dark", "mr", "home-dark-mr-1536x1024.png"]] as const) {
  test(`Home looks the same: ${theme} ${lang}`, async ({ page }) => {
    await page.setViewportSize({ width: 1536, height: 1024 });
    await open(page, `/${lang}/?check=1`, theme);
    await settled(page);
    await shot(page, name);
  });
}

// last, because it creates a SECOND check (the screenshots above must show a single one)
test("switching the check in the sidebar keeps you on Home for that check", async ({ page, request }) => {
  await request.post("/api/checks", { data: { N: 30, P: 60, K: 20, temperature: 28, humidity: 60, ph: 6.9, rainfall: 55 } });
  await open(page, "/en/?check=1");
  await settled(page);
  await page.getByTestId("recent-checks").getByRole("link", { name: /#2/ }).click();
  await expect(page).toHaveURL(/\?check=2$/);
  await settled(page);
  await expect(page.getByTestId("current-check")).toContainText("#2");
  await expect(page.getByTestId("hero-crop")).not.toContainText("Rice");
});

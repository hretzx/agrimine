import { expect, test, type Page } from "@playwright/test";

/**
 * The sidebar, in the situations a real person meets: tall and short windows, several saved checks, other pages, Marathi.
 * One shared database (six checks), so the tests run in order; run the whole file, not single tests.
 */
test.describe.configure({ mode: "serial" });

const CHECKS = [
  { N: 90, P: 42, K: 43, temperature: 20.9, humidity: 82, ph: 6.5, rainfall: 202.9 },
  { N: 30, P: 60, K: 20, temperature: 28, humidity: 60, ph: 6.9, rainfall: 55 },
  { N: 20, P: 130, K: 200, temperature: 23, humidity: 92, ph: 6, rainfall: 110 },
  { N: 100, P: 17, K: 50, temperature: 28, humidity: 92, ph: 6.4, rainfall: 25 },
  { N: 80, P: 48, K: 20, temperature: 22, humidity: 65, ph: 6.2, rainfall: 85 },
  { N: 40, P: 68, K: 80, temperature: 19, humidity: 17, ph: 7.3, rainfall: 80 },
];
const SIZES = [
  { w: 1920, h: 1080 }, { w: 1536, h: 1024 }, { w: 1366, h: 768 }, { w: 1280, h: 600 }, { w: 1024, h: 700 }, { w: 1366, h: 500 },
];
const NOON = new Date("2026-10-20T10:00:00");

async function open(page: Page, path: string, theme: "light" | "dark" = "light") {
  await page.clock.setFixedTime(NOON);
  await page.addInitScript((t) => { if (!localStorage.getItem("theme")) localStorage.setItem("theme", t); }, theme);
  await page.goto(path);
  await page.evaluate(() => document.fonts.ready);
  await expect(page.getByTestId("current-check")).toBeVisible();
  await expect(page.getByTestId("recent-checks")).toBeVisible();
  await expect(page.getByRole("navigation").getByRole("link").nth(2)).toContainText(/Good|Moderate|Needs attention|चांगले|मध्यम|लक्ष द्यावे/);
  await page.waitForTimeout(300);
}
const box = async (page: Page, testId: string) => (await page.getByTestId(testId).boundingBox())!;

test("seed six checks", async ({ request }) => {
  for (const c of CHECKS) expect((await request.post("/api/checks", { data: c })).status()).toBe(201);
});

for (const size of SIZES) {
  test(`nothing is drawn on top of the landscape or the profile bar, and everything is reachable: ${size.w}x${size.h}`, async ({ page }) => {
    await page.setViewportSize({ width: size.w, height: size.h });
    await open(page, "/en/?check=1");
    const scroll = await box(page, "side-scroll");
    const art = await box(page, "side-art");
    const rem = await page.evaluate(() => parseFloat(getComputedStyle(document.documentElement).fontSize));
    // the scrolling part ends where the landscape begins: they never share space
    expect(scroll.y + scroll.height, "scroll area ends above the landscape").toBeLessThanOrEqual(art.y + 1);
    expect(art.height, "the landscape keeps at least 9.5rem").toBeGreaterThanOrEqual(9.5 * rem - 1);
    const profile = await box(page, "profile");
    expect(profile.y).toBeGreaterThanOrEqual(art.y);                        // the profile bar sits on the landscape, inside the window
    expect(profile.y + profile.height).toBeLessThanOrEqual(size.h);
    // the last thing in the list can be scrolled into view, and then it really is the TOPMOST thing at its position
    const viewAll = page.getByRole("link", { name: "View all checks" });
    await viewAll.scrollIntoViewIfNeeded();
    const covered = await viewAll.evaluate((el) => {
      const r = el.getBoundingClientRect();
      const top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      return !(top === el || el.contains(top));
    });
    expect(covered, "something is painted over 'View all checks'").toBe(false);
    const after = await viewAll.boundingBox();
    expect(after!.y + after!.height, "'View all checks' ends above the landscape").toBeLessThanOrEqual(art.y + 1);
    // the page itself must not need sideways scrolling
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });
}

test("the scrolling part is a labelled, keyboard-reachable region", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 600 });
  await open(page, "/en/?check=1");
  const region = page.getByRole("region", { name: "Farm" });
  await expect(region).toHaveAttribute("tabindex", "0");
  const scrollable = await region.evaluate((el) => el.scrollHeight > el.clientHeight);
  expect(scrollable, "at 600px tall the list needs scrolling").toBe(true);
  await region.focus();                                                     // ... and keyboard users can reach it and scroll
  await page.keyboard.press("End");
  await expect.poll(() => region.evaluate((el) => el.scrollTop), { message: "keyboard scrolling is animated: wait for it to land" }).toBeGreaterThan(0);
  await page.keyboard.press("Home");
  await expect.poll(() => region.evaluate((el) => el.scrollTop)).toBe(0);
});

test("no decorative controls: nothing in the sidebar is an input, and the profile bar is not a button", async ({ page }) => {
  await open(page, "/en/?check=1");
  await expect(page.locator("aside input")).toHaveCount(0);
  await expect(page.getByTestId("profile").getByRole("button")).toHaveCount(0);
  // every interactive thing in the sidebar goes somewhere
  const dead = await page.locator("aside a").evaluateAll((els) => els.filter((a) => !(a as HTMLAnchorElement).getAttribute("href")).length);
  expect(dead).toBe(0);
});

test("choosing a recent check keeps you on the page you are on", async ({ page }) => {
  await open(page, "/en/doctor/?check=1");
  await page.getByTestId("recent-checks").getByRole("link", { name: /#3/ }).click();
  await expect(page).toHaveURL(/\/en\/doctor\/\?check=3$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Crop Doctor");
  await expect(page.getByTestId("current-check")).toContainText("#3");
  await expect(page.getByRole("navigation").getByRole("link").nth(2)).toHaveAttribute("aria-current", "page");
});

test("'View all checks' opens a real list of every check, and Open goes to Home for that check", async ({ page, request }) => {
  await open(page, "/en/?check=1");
  await page.getByRole("link", { name: "View all checks" }).click();
  await expect(page).toHaveURL(/\/en\/checks\/\?check=1$/);
  const all = await (await request.get("/api/checks?limit=100")).json();
  expect(all).toHaveLength(6);
  const rows = page.getByTestId("all-checks").getByRole("listitem");
  await expect(rows).toHaveCount(6);
  await expect(rows.first()).toContainText("#6");                            // newest first
  for (const c of all) await expect(page.getByTestId("all-checks")).toContainText(c.predicted_crop.label);
  await rows.nth(2).getByRole("link", { name: "Open" }).click();            // #4
  await expect(page).toHaveURL(/\/en\/\?check=4$/);
  await expect(page.getByTestId("current-check")).toContainText("#4");
});

test("choosing a recent check from the list page opens Home (not a page that cannot show it)", async ({ page }) => {
  await open(page, "/en/checks/?check=1");
  await expect(page.getByTestId("recent-checks").getByRole("listitem")).toHaveCount(4);   // the sidebar lists the four newest (#6 to #3)
  await page.getByTestId("recent-checks").getByRole("link", { name: /#5/ }).click();
  await expect(page).toHaveURL(/\/en\/\?check=5$/);
});

// Dates change by the day: give every date the same text instead of masking it (a mask also covers dates scrolled out of
// view, which would hide the very area these pictures are for).
const shot = async (page: Page, name: string) => {
  await page.evaluate(() => document.querySelectorAll('[data-testid="date"]').forEach((el) => { el.textContent = "20 Oct"; }));
  await expect(page.locator("aside")).toHaveScreenshot(name);
};
for (const [w, h, route, theme, name] of [
  [1366, 768, "/en/?check=1", "light", "sidebar-light-1366x768.png"],
  [1280, 600, "/en/?check=1", "light", "sidebar-light-1280x600.png"],
  [1366, 500, "/en/grow/?check=1", "dark", "sidebar-dark-1366x500.png"],
  [1920, 1080, "/mr/?check=1", "dark", "sidebar-mr-dark-1920x1080.png"],
] as const) {
  test(`the sidebar looks the same: ${name}`, async ({ page }) => {
    await page.setViewportSize({ width: w, height: h });
    await open(page, route, theme);
    await shot(page, name);
  });
}

/**
 * The class of bug that came back three times: each fix was checked at a few hand-picked desktop sizes (or on Home only), so the
 * next window size or page broke it. This walks EVERY page x both languages x desktop, tablet and phone widths x scrolled to the
 * top, middle and bottom, and checks the sidebar's geometry each time.
 */
const EVERY_PAGE = ["", "check/", "grow/", "doctor/", "plan-b/", "teachers/", "teachers/id3/", "teachers/naive-bayes/", "teachers/kmeans/", "teachers/apriori/", "teachers/hierarchical/", "checks/"];
const EVERY_SIZE = [[1920, 1200], [1536, 1024], [1366, 768], [1280, 600], [1024, 700], [800, 900], [600, 800], [390, 844]] as const;

for (const [w, h] of EVERY_SIZE) {
  test(`the sidebar is whole on every page and language, scrolled anywhere, at ${w}x${h}`, async ({ page }) => {
    await page.setViewportSize({ width: w, height: h });
    for (const lang of ["en", "mr"]) for (const path of EVERY_PAGE) {
      const where = `${lang}/${path || "home"} at ${w}x${h}`;
      await page.goto(`/${lang}/${path}?check=1`);
      await page.evaluate(() => document.fonts.ready);
      await expect(page.getByRole("navigation").getByRole("link")).toHaveCount(5);
      await page.waitForTimeout(500);
      const links = page.getByRole("navigation").getByRole("link");
      for (const frac of [0, 0.5, 1]) {
        await page.evaluate((f) => scrollTo(0, (document.documentElement.scrollHeight - innerHeight) * f), frac);
        const g = await page.evaluate(() => {
          const rect = (sel: string) => document.querySelector(sel)!.getBoundingClientRect();
          const aside = rect("aside"), scroll = rect('[data-testid="side-scroll"]'), art = document.querySelector('[data-testid="side-art"]')!.getBoundingClientRect();
          const main = rect("main");
          return { top: aside.top, height: aside.height, width: aside.width, scrollBottom: scroll.bottom, artTop: art.top, artHeight: art.height, mainWidth: main.width,
                   rem: parseFloat(getComputedStyle(document.documentElement).fontSize), sideways: document.documentElement.scrollWidth > innerWidth };
        });
        const at = `${where}, scrolled to ${frac}`;
        expect(g.mainWidth, `the page keeps room to be read, ${at}`).toBeGreaterThan(Math.min(w - 40, 520));
        expect(g.sideways, `no sideways scrolling, ${at}`).toBe(false);
        if (w >= 768) {
          expect(Math.abs(g.top), `sidebar stays at the top, ${at}`).toBeLessThanOrEqual(1);
          expect(Math.abs(g.height - h), `sidebar fills the window, ${at}`).toBeLessThanOrEqual(1);
          expect(g.scrollBottom, `no text drawn over the picture, ${at}`).toBeLessThanOrEqual(g.artTop + 1);
          expect(g.artHeight, `the picture keeps its own space, ${at}`).toBeGreaterThanOrEqual(9.5 * g.rem - 1);
        } else {
          expect(g.width, `on a phone the sidebar is a header across the top, ${at}`).toBeGreaterThanOrEqual(w - 1);
          expect(g.height, `on a phone the header is short, ${at}`).toBeLessThan(h / 3);
        }
      }
      await page.evaluate(() => scrollTo(0, 0));
      for (let i = 0; i < 5; i++) {                       // every destination can be reached, even where the row scrolls sideways
        await links.nth(i).scrollIntoViewIfNeeded();
        const box = (await links.nth(i).boundingBox())!;
        expect(box.x + box.width, `link ${i + 1} is on screen, ${where}`).toBeLessThanOrEqual(w + 1);
        expect(box.x, `link ${i + 1} starts on screen, ${where}`).toBeGreaterThanOrEqual(-1);
      }
    }
  });
}

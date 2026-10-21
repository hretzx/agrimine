import { expect, test, type Page } from "@playwright/test";

/**
 * The whole UI on a phone (390x844, and a small 360x640 one): every page fits the screen, nothing is cut off, the controls are
 * big enough to tap, the current check is one tap away, the wide tables scroll inside their own box. Shares the "pages" server
 * (own database), so it starts by creating the checks it needs.
 */
test.describe.configure({ mode: "serial" });

const RICE = { N: 90, P: 42, K: 43, temperature: 20.9, humidity: 82, ph: 6.5, rainfall: 202.9 };
const NOON = new Date("2026-10-20T10:00:00");
const PAGES = ["", "check/", "grow/", "doctor/", "plan-b/", "teachers/", "teachers/id3/", "teachers/naive-bayes/", "teachers/kmeans/", "teachers/apriori/", "teachers/hierarchical/", "checks/"];
const PHONES = [[390, 844], [360, 640]] as const;

async function open(page: Page, path: string) {
  await page.clock.setFixedTime(NOON);
  await page.goto(path);
  await page.evaluate(() => document.fonts.ready);
  await expect(page.getByRole("status").filter({ hasText: "Loading" })).toHaveCount(0, { timeout: 15_000 });
  await page.waitForTimeout(500);
}

test("seed a check", async ({ request }) => {
  expect((await request.post("/api/checks", { data: RICE })).ok()).toBe(true);
});

for (const [w, h] of PHONES) {
  test(`on a ${w}x${h} phone every page fits: no sideways scroll, nothing wider than the screen, taps are big enough`, async ({ page }) => {
    await page.setViewportSize({ width: w, height: h });
    const problems: string[] = [];
    for (const lang of ["en", "mr"]) for (const path of PAGES) {
      await open(page, `/${lang}/${path}?check=1`);
      const where = `${lang}/${path || "home"} at ${w}x${h}`;
      const r = await page.evaluate(() => {
        const wide = [...document.querySelectorAll("body *")].filter((e) => {
          const b = e.getBoundingClientRect();
          if (b.width === 0 || b.right <= innerWidth + 1) return false;
          for (let p = e.parentElement; p; p = p.parentElement) {          // a box that clips or scrolls its own content may hold wider things
            const o = getComputedStyle(p);
            if (o.overflowX !== "visible" && p !== document.body && p !== document.documentElement) return false;
          }
          return true;
        });
        const small = [...document.querySelectorAll('a[href], button, input, select, [role="combobox"], [role="slider"]')].filter((e) => {
          const b = e.getBoundingClientRect(), s = getComputedStyle(e);
          return b.width > 0 && s.visibility !== "hidden" && (b.height < 34 || b.width < 34) && !e.closest('[data-testid="skip-link"]') && e.tagName !== "INPUT";
        }).map((e) => `${e.tagName} ${(e.textContent ?? "").trim().slice(0, 20) || e.getAttribute("aria-label")} ${Math.round(e.getBoundingClientRect().width)}x${Math.round(e.getBoundingClientRect().height)}`);
        return { sideways: document.documentElement.scrollWidth - innerWidth, wide: wide.slice(0, 3).map((e) => `${e.tagName}.${String(e.getAttribute("class")).slice(0, 50)}`), small, smallInputs: [...document.querySelectorAll("input:not([aria-hidden=true]):not([type=range]):not([type=checkbox])")].filter((i) => parseFloat(getComputedStyle(i).fontSize) < 16).length };
      });
      if (r.sideways > 0) problems.push(`${where}: scrolls sideways by ${r.sideways}px`);
      if (r.wide.length) problems.push(`${where}: sticks out past the screen: ${r.wide.join(", ")}`);
      if (r.small.length) problems.push(`${where}: taps under 34px (about 9mm): ${r.small.join(", ")}`);
      if (r.smallInputs) problems.push(`${where}: ${r.smallInputs} input(s) under 16px, so phones zoom in on focus`);
    }
    expect(problems).toEqual([]);
  });
}

test("on a phone the links are one row of tabs that scrolls sideways, starting on the current page; the current check opens with one tap", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await open(page, "/en/teachers/?check=1");                       // the last tab: it must start scrolled into view
  const row = page.getByTestId("nav-tabs"), links = row.getByRole("link");
  await expect(links).toHaveCount(5);
  const tops = await links.evaluateAll((els) => els.map((e) => Math.round(e.getBoundingClientRect().top)));
  expect(new Set(tops).size, "all tabs sit on one line").toBe(1);
  const m = await row.evaluate((e) => ({ scroll: e.scrollWidth, client: e.clientWidth, left: e.scrollLeft }));
  expect(m.scroll, "the row is wider than the screen, so it scrolls").toBeGreaterThan(m.client);
  expect(m.left, "it opened scrolled to the current tab").toBeGreaterThan(0);
  const here = (await links.nth(4).boundingBox())!;
  expect(here.x).toBeGreaterThanOrEqual(0);
  expect(here.x + here.width).toBeLessThanOrEqual(390);
  await row.evaluate((e) => { e.scrollLeft = 0; });                // scrolling back reveals the first tab
  await expect.poll(async () => (await links.nth(0).boundingBox())!.x, { message: "the first tab comes into view" }).toBeGreaterThanOrEqual(0);   // (the row scrolls smoothly)
  expect((await page.evaluate(() => document.documentElement.scrollWidth)), "the page itself does not scroll sideways").toBeLessThanOrEqual(390);
  await links.nth(2).click();                                      // a tab works as a link, and the next page starts on its own tab
  await expect(page).toHaveURL(/\/en\/doctor\//);
  await expect(page.getByTestId("current-check")).toBeHidden();
  const toggle = page.getByTestId("side-checks-toggle");
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
  await expect(page.getByTestId("current-check")).toBeVisible();
  await expect(page.getByTestId("current-check")).toContainText("Rice");
  await toggle.click();
  await expect(page.getByTestId("current-check")).toBeHidden();
});

test("on a desktop the phone toggle does not exist and the current check is always shown", async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await open(page, "/en/grow/?check=1");
  await expect(page.getByTestId("side-checks-toggle")).toBeHidden();
  await expect(page.getByTestId("current-check")).toBeVisible();
});

test("the comparison table scrolls inside its own box on a phone (the page does not)", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await open(page, "/en/grow/?check=1");
  const box = page.getByTestId("compare").getByRole("region");
  const m = await box.evaluate((e) => ({ scroll: e.scrollWidth, client: e.clientWidth, page: document.documentElement.scrollWidth }));
  expect(m.scroll).toBeGreaterThan(m.client);                    // it really is wider than the screen ...
  expect(m.page).toBeLessThanOrEqual(390);                       // ... and the page is not
  await box.focus();
  await expect(box).toBeFocused();                               // a keyboard user can reach it (and the arrow keys then scroll it)
  expect(await box.evaluate((e) => { e.scrollLeft = 80; return e.scrollLeft; })).toBeGreaterThan(0);
});

for (const [name, path, theme, lang] of [
  ["home", "", "light", "en"], ["grow", "grow/", "dark", "mr"], ["doctor", "doctor/", "light", "en"], ["planb", "plan-b/", "light", "mr"],
  ["teachers", "teachers/", "light", "en"], ["id3", "teachers/id3/", "dark", "en"], ["checks", "checks/", "light", "en"], ["nb", "teachers/naive-bayes/", "light", "mr"], ["km", "teachers/kmeans/", "dark", "en"], ["apr", "teachers/apriori/", "light", "mr"], ["hier", "teachers/hierarchical/", "dark", "en"], ["check", "check/", "light", "mr"],
] as const) {
  test(`phone page looks the same: ${name} ${theme} ${lang}`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.addInitScript((t) => localStorage.setItem("theme", t), theme);
    await open(page, `/${lang}/${path}?check=1`);
    await expect(page).toHaveScreenshot(`phone-${name}-${theme}-${lang}.png`, { fullPage: true, mask: [page.getByTestId("date")] });
  });
}

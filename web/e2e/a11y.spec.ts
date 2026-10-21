import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

/**
 * Accessibility, measured on the real rendered pages (axe-core): colour contrast, names for buttons and links, form labels,
 * landmarks, heading order. Every page, light and dark, English and Marathi. One shared database, so run the whole file.
 */
test.describe.configure({ mode: "serial" });

const CHECKS = [
  { N: 90, P: 42, K: 43, temperature: 20.9, humidity: 82, ph: 6.5, rainfall: 202.9 },
  { N: 40, P: 68, K: 80, temperature: 19, humidity: 17, ph: 7.3, rainfall: 80 },
];
const PAGES = ["", "check/", "grow/", "doctor/", "plan-b/", "teachers/", "teachers/id3/", "teachers/naive-bayes/", "teachers/kmeans/", "teachers/apriori/", "teachers/hierarchical/", "checks/"];

test.beforeAll(async ({ request }) => {
  for (const values of CHECKS) expect((await request.post("/api/checks", { data: values })).ok()).toBe(true);
});

async function ready(page: Page, path: string, theme: string) {
  await page.addInitScript((t) => localStorage.setItem("theme", t), theme);
  await page.goto(path);
  await page.evaluate(() => document.fonts.ready);
  if (path.includes("check=") && (page.viewportSize()?.width ?? 0) >= 768) {   // on a phone the current check is folded away until the toggle is tapped
    await expect(page.getByTestId("current-check")).toBeVisible();
    await expect(page.getByTestId("recent-checks")).toBeVisible();
  }
  await page.waitForTimeout(700);                           // charts and sidebar chip finish drawing
}

for (const lang of ["en", "mr"]) {
  for (const theme of ["light", "dark"]) {
    for (const p of PAGES) {
      test(`axe: /${lang}/${p} (${theme})`, async ({ page }) => {
        await page.setViewportSize({ width: 1536, height: 1024 });
        await ready(page, `/${lang}/${p}?check=1`.replace("/?", "/?"), theme);
        const { violations } = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
        const report = violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.length} node(s), e.g. ${v.nodes[0].target.join(" ")} | ${v.nodes[0].failureSummary?.split("\n")[1] ?? ""}`);
        expect(report, `${violations.length} kind(s) of violation`).toEqual([]);
      });
    }
  }
}

/** The same checks on a phone: the sidebar is a header, the pages are one column, the wide comparison tables scroll. */
for (const lang of ["en", "mr"]) {
  for (const p of PAGES) {
    test(`axe on a phone: /${lang}/${p}`, async ({ page }) => {
      await page.setViewportSize({ width: 390, height: 844 });
      await ready(page, `/${lang}/${p}?check=1`, "light");
      const { violations } = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
      const report = violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.length} node(s), e.g. ${v.nodes[0].target.join(" ")} | ${v.nodes[0].failureSummary?.split("\n")[1] ?? ""}`);
      expect(report, `${violations.length} kind(s) of violation`).toEqual([]);
    });
  }
}

/** What the browser draws for an element, enough to tell "focused" from "not focused". */
const LOOK = (el: Element) => {
  const c = getComputedStyle(el);
  return [c.outlineStyle, c.outlineWidth, c.outlineColor, c.boxShadow, c.backgroundColor, c.borderColor, c.color, c.textDecorationLine].join("|");
};
const TABBABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [role="slider"], [tabindex]:not([tabindex="-1"])';

for (const theme of ["light", "dark"]) {
  for (const p of PAGES) {
    test(`keyboard: every control on /en/${p} shows where the focus is (${theme})`, async ({ page }) => {
      await page.setViewportSize({ width: 1536, height: 1024 });
      await ready(page, `/en/${p}?check=1`, theme);
      await page.addStyleTag({ content: "*{transition:none!important;animation:none!important}" });
      // how every tabbable element looks before anything is focused
      const before = await page.evaluate(([sel, fn]) => {
        const look = new Function("el", `return (${fn})(el)`) as (el: Element) => string;
        const out: string[] = [];
        document.querySelectorAll(sel).forEach((el, i) => { (el as HTMLElement).dataset.tabIdx = String(i); out[i] = look(el); });
        return out;
      }, [TABBABLE, LOOK.toString()] as const);
      expect(before.length).toBeGreaterThan(5);
      await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
      const seen = new Set<string>();
      const missing: string[] = [];
      for (let i = 0; i < before.length + 12; i++) {
        await page.keyboard.press("Tab");
        const r = await page.evaluate(([fn]) => {
          const look = new Function("el", `return (${fn})(el)`) as (el: Element) => string;
          const el = document.activeElement as HTMLElement | null;
          if (!el || el === document.body || el.dataset.tabIdx === undefined) return null;
          const box = el.getBoundingClientRect();
          return { idx: Number(el.dataset.tabIdx), now: look(el), name: (el.getAttribute("aria-label") || el.textContent || el.tagName).trim().slice(0, 40), visible: box.width > 0 && box.height > 0 };
        }, [LOOK.toString()] as const);
        if (!r || seen.has(String(r.idx)) || !r.visible) continue;
        seen.add(String(r.idx));
        if (r.now === before[r.idx]) missing.push(r.name);
      }
      expect(seen.size, "the Tab key should reach the controls").toBeGreaterThan(5);
      expect(missing, "controls that look the same when focused").toEqual([]);
    });
  }
}

for (const lang of ["en", "mr"]) {
  test(`keyboard: the first Tab offers "skip to content" and it moves focus to the page (${lang})`, async ({ page }) => {
    await page.setViewportSize({ width: 1536, height: 1024 });
    await ready(page, `/${lang}/grow/?check=1`, "light");
    await page.keyboard.press("Tab");
    const skip = page.getByTestId("skip-link");
    await expect(skip).toBeFocused();
    await expect(skip).toBeInViewport();                      // visible when focused, not just present
    expect((await skip.boundingBox())!.width).toBeGreaterThan(80);
    await page.keyboard.press("Enter");
    await expect(page.locator("main#main")).toBeFocused();
    await page.keyboard.press("Tab");                          // the next stop is inside the page, not the sidebar again
    expect(await page.evaluate(() => !!document.activeElement?.closest("main"))).toBe(true);
  });
}

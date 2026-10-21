import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

/**
 * The animations, measured in a real browser: this is the only group that runs WITH motion (the others use "reduce motion").
 * Each test samples what the browser really draws, frame by frame, while something happens, and checks the shape of the movement:
 * it starts where it was, passes through in-between values, and ends where it should. A second block checks that a visitor who
 * asked for reduced motion gets no movement at all. Shares one database, so run the whole file.
 */
test.describe.configure({ mode: "serial" });

const RICE = { N: 90, P: 42, K: 43, temperature: 20.9, humidity: 82, ph: 6.5, rainfall: 202.9 };

test.beforeAll(async ({ request }) => {
  expect((await request.post("/api/checks", { data: RICE })).ok()).toBe(true);
});

/** Read `expr` (a function of the element, as source text) from the first element matching `selector`, once per frame, for `ms` milliseconds. */
const record = (page: Page, selector: string, expr: string, ms = 1200) =>
  page.evaluate(async ([sel, source, span]) => {
    const read = new Function("el", `return (${source})`) as (el: Element) => number;
    const out: number[] = [];
    const t0 = performance.now();
    while (performance.now() - t0 < Number(span)) {
      const el = document.querySelector(String(sel));
      if (el) out.push(read(el));
      await new Promise((r) => requestAnimationFrame(r));
    }
    return out;
  }, [selector, expr, String(ms)]);

const OPACITY = "Number(getComputedStyle(el).opacity)";

/** Like `record`, but installed BEFORE the page loads (so it survives a navigation): read it back with `recorded(page, name)`. */
const recordFromStart = (page: Page, name: string, selector: string, expr: string, ms = 1500) =>
  page.addInitScript(([key, sel, source, span]) => {
    const read = new Function("el", `return (${source})`) as (el: Element) => number;
    const out: number[] = [];
    ((window as unknown as { __rec?: Record<string, number[]> }).__rec ??= {})[String(key)] = out;
    const t0 = performance.now();
    const tick = () => {
      if (performance.now() - t0 > Number(span)) return;
      const el = document.querySelector(String(sel));
      if (el) out.push(read(el));
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [name, selector, expr, String(ms)]);
const recorded = async (page: Page, name: string, wait = 1700) => {
  await page.waitForTimeout(wait);
  return page.evaluate((key) => (window as unknown as { __rec: Record<string, number[]> }).__rec[key], name);
};

const between = (values: number[], lo: number, hi: number) => values.some((v) => v > lo + 0.02 * (hi - lo) && v < hi - 0.02 * (hi - lo));

test.describe("with animations on", () => {
  test.use({ reducedMotion: "no-preference" });

  test("a page's cards fade up when it opens: from see-through to solid, passing through the in-between", async ({ page }) => {
    await page.setViewportSize({ width: 1536, height: 1024 });
    await recordFromStart(page, "fade", "main section", OPACITY);
    await page.goto("/en/grow/?check=1");
    const opacity = await recorded(page, "fade");
    expect(opacity.length).toBeGreaterThan(10);
    expect(Math.min(...opacity), "it starts transparent").toBeLessThan(0.3);
    expect(between(opacity, 0, 1), "it passes through in-between values (it is animated, not switched)").toBe(true);
    expect(opacity.at(-1), "and ends fully visible").toBe(1);
  });

  test("the cards of a page arrive one after another, not all at once", async ({ page }) => {
    await page.setViewportSize({ width: 1536, height: 1024 });
    await page.addInitScript(() => {
      const first = new Map<Element, number>();
      (window as unknown as { __arrival: () => number[] }).__arrival = () => [...first.values()].sort((a, b) => a - b);
      const t0 = performance.now();
      const tick = () => {
        if (performance.now() - t0 > 2200) return;
        document.querySelectorAll("main section").forEach((c) => { if (!first.has(c) && Number(getComputedStyle(c).opacity) > 0.2) first.set(c, performance.now() - t0); });
        requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
    await page.goto("/en/?check=1");
    await page.waitForTimeout(2400);
    const arrival = await page.evaluate(() => (window as unknown as { __arrival: () => number[] }).__arrival());
    expect(arrival.length, "several cards appeared").toBeGreaterThan(8);
    expect(arrival.at(-1)! - arrival[0], "the last card arrives clearly after the first").toBeGreaterThan(150);
    expect(new Set(arrival.map((t) => Math.round(t / 16))).size, "in more than one step, not all in the same frame").toBeGreaterThanOrEqual(2);
  });

  test("progress bars grow from empty", async ({ page }) => {
    await page.setViewportSize({ width: 1536, height: 1024 });
    await recordFromStart(page, "bar", '[role="progressbar"] > div > div', "el.getBoundingClientRect().width", 2000);
    await page.goto("/en/grow/?check=1");
    const widths = await recorded(page, "bar", 2200);
    expect(Math.min(...widths)).toBeLessThan(2);
    expect(between(widths, 0, Math.max(...widths))).toBe(true);
    expect(Math.max(...widths)).toBeGreaterThan(20);
  });

  test("the sidebar stays mounted between pages and its active pill glides to the new item", async ({ page }) => {
    await page.setViewportSize({ width: 1536, height: 1024 });
    await page.goto("/en/?check=1");
    await expect(page.getByTestId("hero-crop")).toBeVisible();
    await page.evaluate(() => { (document.querySelector("aside") as HTMLElement).dataset.marker = "same-sidebar"; });
    const pill = '[aria-current="page"] > span[aria-hidden="true"]';
    const homeTop = await page.locator(pill).evaluate((e) => e.getBoundingClientRect().top);
    const sampling = record(page, pill, "el.getBoundingClientRect().top", 900);
    await page.getByRole("navigation").getByRole("link", { name: /What should I grow/ }).click();
    const tops = await sampling;
    await expect(page).toHaveURL(/\/en\/grow\//);
    expect(await page.locator("aside").getAttribute("data-marker"), "the sidebar was not rebuilt").toBe("same-sidebar");
    const growTop = await page.locator(pill).evaluate((e) => e.getBoundingClientRect().top);
    expect(growTop).toBeGreaterThan(homeTop + 20);
    expect(between(tops, homeTop, growTop), "the pill passed through places between the two items").toBe(true);
    expect(Math.abs(tops.at(-1)! - growTop)).toBeLessThan(1);
  });

  test("a button dips under the finger and springs back", async ({ page }) => {
    await page.setViewportSize({ width: 1536, height: 1024 });
    await page.goto("/en/?check=1");
    const link = page.locator("main").getByRole("link", { name: "New soil check" });      // the green header button, not the sidebar pencil
    await expect(link).toBeVisible();
    const box = (await link.boundingBox())!;
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.waitForTimeout(250);
    const lifted = await link.evaluate((e) => getComputedStyle(e).transform);
    await page.mouse.down();
    await page.waitForTimeout(250);
    const pressed = await link.evaluate((e) => Number(getComputedStyle(e).transform.match(/matrix\(([^,]+)/)?.[1] ?? 1));
    expect(pressed, "pressed: smaller than normal").toBeLessThan(0.985);
    expect(lifted, "hovering: raised, not shrunk").toMatch(/matrix\(1, 0, 0, 1, 0, -/);
    await page.mouse.up({ button: "left" });
  });

  test("switching the theme reveals the new one as a growing circle, and the icon turns into the other", async ({ page }) => {
    await page.setViewportSize({ width: 1536, height: 1024 });
    await page.addInitScript(() => {
      localStorage.setItem("theme", "light");
      const real = document.startViewTransition?.bind(document);
      (window as unknown as { __reveals: number }).__reveals = 0;
      if (real) document.startViewTransition = ((cb: () => void) => { (window as unknown as { __reveals: number }).__reveals++; return real(cb); }) as typeof document.startViewTransition;
    });
    await page.goto("/en/?check=1");
    const toggle = page.getByRole("button", { name: /dark/i });
    await expect(toggle.locator("svg.lucide-moon")).toBeVisible();
    await toggle.click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await expect(page.getByRole("button", { name: /light/i }).locator("svg.lucide-sun")).toBeVisible();      // the icon changed to a sun
    expect(await page.evaluate(() => (window as unknown as { __reveals: number }).__reveals), "a view transition (the circle) ran").toBe(1);
    expect(await page.evaluate(() => localStorage.getItem("theme"))).toBe("dark");
  });

  test("a switch's selected pill glides from one option to the next", async ({ page }) => {
    await page.setViewportSize({ width: 1536, height: 1024 });
    await page.goto("/en/teachers/hierarchical/?check=1");
    const group = page.getByRole("group", { name: "Linkage" });
    await expect(group).toBeVisible();
    const pill = '[aria-label="Linkage"] [aria-pressed="true"] > span[aria-hidden="true"]';
    const before = await page.locator(pill).evaluate((e) => e.getBoundingClientRect().left);
    const sampling = record(page, pill, "el.getBoundingClientRect().left", 800);
    await group.getByRole("button", { name: "Single", exact: true }).click();
    const lefts = await sampling;
    const after = await page.locator(pill).evaluate((e) => e.getBoundingClientRect().left);
    expect(after).toBeGreaterThan(before + 40);
    expect(between(lefts, before, after), "the pill passed through places between the options").toBe(true);
  });

  test("on a phone the current-check panel opens and closes smoothly", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/en/grow/?check=1");
    await expect(page.getByTestId("side-checks-toggle")).toBeVisible();
    const open = record(page, "#side-checks", "el.getBoundingClientRect().height", 700);
    await page.getByTestId("side-checks-toggle").click();
    const heights = await open;
    expect(heights[0]).toBeLessThan(2);
    expect(between(heights, 0, Math.max(...heights)), "it grew gradually").toBe(true);
    await expect(page.getByTestId("current-check")).toBeVisible();
    await page.getByTestId("side-checks-toggle").click();
    await expect(page.getByTestId("current-check")).toBeHidden();                 // closed means gone for the keyboard and screen readers too
  });
});

test.describe("accessibility with animations on", () => {
  test.use({ reducedMotion: "no-preference" });

  for (const path of ["/en/?check=1", "/en/grow/?check=1", "/en/doctor/?check=1", "/mr/teachers/kmeans/?check=1"]) {
    for (const theme of ["light", "dark"]) {
      test(`axe finds nothing once the animations have settled: ${path} ${theme}`, async ({ page }) => {
        await page.setViewportSize({ width: 1536, height: 1024 });
        await page.addInitScript((t) => localStorage.setItem("theme", t), theme);
        await page.goto(path);
        await page.waitForTimeout(2200);                                              // cards, bars, gauges and the ring have all arrived
        const { violations } = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
        expect(violations.map((v) => `${v.id}: ${v.nodes[0].target.join(" ")}`)).toEqual([]);
      });
    }
  }
});

test.describe("with reduced motion", () => {
  test.use({ reducedMotion: "reduce" });

  test("nothing moves: cards are solid from their first frame, bars are full, the pill jumps, the theme changes at once", async ({ page }) => {
    await page.setViewportSize({ width: 1536, height: 1024 });
    await page.addInitScript(() => {
      localStorage.setItem("theme", "light");
      (window as unknown as { __reveals: number }).__reveals = 0;
      const real = document.startViewTransition?.bind(document);
      if (real) document.startViewTransition = ((cb: () => void) => { (window as unknown as { __reveals: number }).__reveals++; return real(cb); }) as typeof document.startViewTransition;
    });
    await recordFromStart(page, "o", "main section", OPACITY, 1200);
    await recordFromStart(page, "w", '[role="progressbar"] > div > div', "el.getBoundingClientRect().width", 1200);
    await page.goto("/en/grow/?check=1");
    const [o, w] = [await recorded(page, "o", 1400), await recorded(page, "w", 10)];
    expect(o.length).toBeGreaterThan(5);
    expect(Math.min(...o), "never see-through").toBe(1);
    expect(Math.min(...w), "bars are never caught growing").toBeGreaterThan(20);

    const pill = '[aria-current="page"] > span[aria-hidden="true"]';
    const tops = record(page, pill, "el.getBoundingClientRect().top", 700);
    await page.getByRole("navigation").getByRole("link", { name: "Plan B" }).click();
    const seen = new Set((await tops).map((t) => Math.round(t)));
    expect(seen.size, "the pill is at one place, then at the other, never in between").toBeLessThanOrEqual(2);

    await page.getByRole("button", { name: /dark/i }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    expect(await page.evaluate(() => (window as unknown as { __reveals: number }).__reveals), "no circle reveal").toBe(0);
  });
});

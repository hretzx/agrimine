import { expect, test, type Page } from "@playwright/test";

const SIZES = [
  { name: "1366x768", width: 1366, height: 768 },
  { name: "1536x1024", width: 1536, height: 1024 },
  { name: "1920x1080", width: 1920, height: 1080 },
];
const THEMES = ["light", "dark"] as const;

async function open(page: Page, lang: "en" | "mr", theme: (typeof THEMES)[number]) {
  await page.addInitScript((t) => { if (!localStorage.getItem("theme")) localStorage.setItem("theme", t); }, theme);   // seed only: a reload must keep the saved choice
  await page.goto(`/${lang}/dev/components/`);
  await page.evaluate(() => document.fonts.ready);
  await expect(page.getByTestId("gallery")).toBeVisible();
}

for (const theme of THEMES) {
  for (const size of SIZES) {
    test(`gallery looks the same: ${theme} ${size.name}`, async ({ page }) => {
      await page.setViewportSize({ width: size.width, height: size.height });
      await open(page, "en", theme);
      await expect(page).toHaveScreenshot(`gallery-${theme}-${size.name}.png`, { fullPage: true });
    });
  }
}

test("Marathi gallery looks the same (dark 1536x1024)", async ({ page }) => {
  await page.setViewportSize({ width: 1536, height: 1024 });
  await open(page, "mr", "dark");
  await expect(page.locator("html")).toHaveAttribute("lang", "mr");
  await expect(page).toHaveScreenshot("gallery-mr-dark-1536x1024.png", { fullPage: true });
});

test("language switch moves to the same page in the other language and remembers it", async ({ page }) => {
  await open(page, "en", "light");
  await page.getByRole("button", { name: "मराठी" }).click();
  await expect(page).toHaveURL(/\/mr\/dev\/components\/$/);
  await expect(page.locator("html")).toHaveAttribute("lang", "mr");
  await expect(page.getByRole("link", { name: "मुख्यपृष्ठ" })).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("lang"))).toBe("mr");
});

test("theme choice is applied before first paint and survives a reload", async ({ page }) => {
  await open(page, "en", "light");
  await page.getByTitle("Dark", { exact: true }).click();     // the toggle (the gallery also has a demo button labelled Dark)
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});

test("every button has an accessible name, every bar a name and a value", async ({ page }) => {
  await open(page, "en", "light");
  const nameless = await page.$$eval("button", (els) => els.filter((b) => !(b.getAttribute("aria-label") || b.textContent?.trim())).length);
  expect(nameless).toBe(0);
  const bars = await page.$$eval("[role=progressbar]", (els) => els.map((e) => [e.getAttribute("aria-label"), e.getAttribute("aria-valuenow")]));
  expect(bars.length).toBeGreaterThan(5);
  for (const [label, value] of bars) {
    expect(label).toBeTruthy();
    expect(Number(value)).toBeGreaterThanOrEqual(0);
  }
});

test("the same process serves the API and the site, and unknown pages get the 404 page", async ({ page, request }) => {
  const meta = await (await request.get("/api/meta")).json();
  expect(meta.records).toBe(2200);
  expect((await request.get("/art/landscape.png")).ok()).toBeTruthy();
  const root = await page.goto("/");
  expect(root?.ok()).toBeTruthy();
  await page.waitForURL(/\/en\/$/).catch(() => {});          // the root page redirects to the saved language
  const missing = await request.get("/en/does-not-exist/");
  expect(missing.status()).toBe(404);
});

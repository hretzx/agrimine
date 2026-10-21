import { defineConfig } from "@playwright/test";
import os from "node:os";
import path from "node:path";

/**
 * End-to-end and visual tests run against the REAL product: the FastAPI process serving the built site (web/out). Build first
 * (npm run build). PYTHON selects the interpreter, CHROMIUM_PATH the browser.
 *
 * Tests that create soil checks must not share a database, so every group has its OWN server on its own port with its own
 * throw-away database, started empty for every run:
 *   home    home.spec.ts + gallery.spec.ts   port 4173
 *   pages   pages.spec.ts                   port 4174
 *   sidebar sidebar.spec.ts                  port 4175
 *   a11y    a11y.spec.ts                     port 4176
 *   mobile  mobile.spec.ts                   port 4178
 *   lab     lab.spec.ts                      port 4177, and the REAL technical lab (Streamlit) on 8177; the others run with AGRIMINE_LAB=0
 * Baselines live in e2e/__screenshots__; update them on purpose with npm run test:visual:update.
 */
const PYTHON = process.env.PYTHON ?? "python";
const group = (name: string, port: number, testMatch: RegExp, lab = false) => {
  const db = path.join(os.tmpdir(), `agrimine-e2e-${name}.db`);
  return {
    project: { name, testMatch, use: { baseURL: `http://127.0.0.1:${port}` } },
    server: { command: `rm -f "${db}" && ${PYTHON} -m api --port ${port}`, cwd: "..", env: { AGRIMINE_DB: db, AGRIMINE_LAB: lab ? "1" : "0", AGRIMINE_LAB_PORT: String(port + 4000) }, url: `http://127.0.0.1:${port}/api/health`, timeout: 120_000, reuseExistingServer: false },
  };
};
const groups = [group("home", 4173, /(home|gallery)\.spec\.ts$/), group("pages", 4174, /pages\.spec\.ts$/), group("sidebar", 4175, /sidebar\.spec\.ts$/), group("a11y", 4176, /a11y\.spec\.ts$/), group("mobile", 4178, /mobile\.spec\.ts$/), group("lab", 4177, /lab\.spec\.ts$/, true)];

export default defineConfig({
  testDir: "./e2e",
  snapshotPathTemplate: "{testDir}/__screenshots__/{arg}{ext}",
  fullyParallel: true,
  workers: 2,
  reporter: [["list"]],
  // strict on purpose: a changed sentence must fail, not pass as "close enough"
  expect: { toHaveScreenshot: { maxDiffPixels: 40, threshold: 0.1, animations: "disabled" } },
  use: {
    launchOptions: {
      executablePath: process.env.CHROMIUM_PATH ?? "/usr/lib/chromium/chromium",
      args: ["--no-sandbox", "--no-zygote", "--disable-gpu", "--disable-dev-shm-usage", "--disable-crash-reporter"],
    },
  },
  projects: groups.map((g) => g.project),
  webServer: groups.map((g) => g.server),
});

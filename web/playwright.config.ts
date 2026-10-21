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
 *   motion  motion.spec.ts                   port 4179, the only group that runs WITH animations
 *   lab     lab.spec.ts                      port 4177, and the REAL technical lab (Streamlit) on 8177; the others run with AGRIMINE_LAB=0
 * Every group but "motion" runs with the visitor setting "reduce motion" on: the animations then render their final state at once, so
 * screenshots and "is it there yet" checks are deterministic. motion.spec.ts turns animations on and checks that they really happen.
 * Baselines live in e2e/__screenshots__; update them on purpose with npm run test:visual:update.
 */
const PYTHON = process.env.PYTHON ?? "python";
const group = (name: string, port: number, testMatch: RegExp, lab = false, motion = false) => {
  const db = path.join(os.tmpdir(), `agrimine-e2e-${name}.db`);
  return {
    project: { name, testMatch, use: { baseURL: `http://127.0.0.1:${port}`, reducedMotion: motion ? "no-preference" as const : "reduce" as const } },
    server: { command: `rm -f "${db}" && ${PYTHON} -m api --port ${port}`, cwd: "..", env: { AGRIMINE_DB: db, AGRIMINE_LAB: lab ? "1" : "0", AGRIMINE_LAB_PORT: String(port + 4000) }, url: `http://127.0.0.1:${port}/api/health`, timeout: 120_000, reuseExistingServer: false },
  };
};
const groups = [group("home", 4173, /(home|gallery)\.spec\.ts$/), group("pages", 4174, /pages\.spec\.ts$/), group("sidebar", 4175, /sidebar\.spec\.ts$/), group("a11y", 4176, /a11y\.spec\.ts$/), group("mobile", 4178, /mobile\.spec\.ts$/), group("lab", 4177, /lab\.spec\.ts$/, true), group("motion", 4179, /motion\.spec\.ts$/, false, true)];

// Start only the servers of the projects being run (`--project=pages`): every server trains the models, and starting all of them
// for a single project used up the machine's threads.
const asked = process.argv.flatMap((arg, i, all) => (arg.startsWith("--project=") ? [arg.slice(10)] : arg === "--project" ? [all[i + 1]] : []));
const active = asked.length ? groups.filter((g) => asked.includes(g.project.name)) : groups;

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
  webServer: active.map((g) => g.server),
});

// @vitest-environment node
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import en from "@/lib/i18n/dictionaries/en.json";

const ROOT = new URL("../", import.meta.url).pathname;
const files = (dir: string): string[] => readdirSync(dir).flatMap((n) => {
  const p = join(dir, n);
  return statSync(p).isDirectory() ? files(p) : /\.(tsx?|mts)$/.test(n) && !/\.d\.ts$/.test(n) ? [p] : [];
});
const SOURCE = ["app", "components", "lib"].flatMap((d) => files(join(ROOT, d))).map((f) => readFileSync(f, "utf8")).join("\n");
// keys built at run time (t(`tip.${key}`) ...): they are covered by their own tests (every tip, every algorithm, every item word, every linkage)
const DYNAMIC = ["tip.", "algo.", "item.", "hier.m."];

describe("message keys", () => {
  it("every message in the dictionary is used somewhere (no dead text to translate and keep in step)", () => {
    const unused = Object.keys(en).filter((k) => !DYNAMIC.some((d) => k.startsWith(d)) && !SOURCE.includes(`"${k}"`));
    expect(unused).toEqual([]);
  });
  it("every message key used in the code exists in the dictionary", () => {
    const used = [...SOURCE.matchAll(/\bt\(\s*"([\w.]+)"/g)].map((m) => m[1]);
    const missing = used.filter((k) => !(k in en));
    expect(missing).toEqual([]);
    expect(used.length).toBeGreaterThan(50); // the scan itself works
  });
  it("dynamic keys have their full set", () => {
    for (const a of ["id3", "nb", "kmeans", "hier", "apriori", "fp", "regression", "match"]) { expect(en).toHaveProperty([`algo.${a}.name`]); expect(en).toHaveProperty([`algo.${a}.use`]); }
    for (const w of ["low", "medium", "high", "acidic", "neutral", "alkaline"]) expect(en).toHaveProperty([`item.${w}`]);
    for (const m of ["ward", "average", "complete", "single"]) { expect(en).toHaveProperty([`hier.m.${m}`]); expect(en).toHaveProperty([`hier.m.${m}.help`]); }
  });
});

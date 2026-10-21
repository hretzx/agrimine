import type { FeatureInfo, Readings } from "@/lib/api/client";

export type ReadingProblem = "required" | "number" | "range";

/** What is wrong with one typed value, or undefined when it is fine. The API stays the judge; this only avoids pointless requests. */
export function readingProblem(f: Pick<FeatureInfo, "lo" | "hi">, raw: string): ReadingProblem | undefined {
  if (raw.trim() === "") return "required";
  const n = Number(raw);
  if (!Number.isFinite(n)) return "number";
  if (n < f.lo || n > f.hi) return "range";
  return undefined;
}

/** The typed strings as a Readings object, or undefined while any of them has a problem. */
export function parseReadings(features: FeatureInfo[], typed: Record<string, string>): Readings | undefined {
  if (features.length === 0) return undefined;
  const out: Record<string, number> = {};
  for (const f of features) {
    const raw = typed[f.key];
    if (raw === undefined || readingProblem(f, raw)) return undefined;
    out[f.key] = Number(raw);
  }
  return out as unknown as Readings;
}

/** A number as the text a person would type into the box (no 1e-7 or trailing zeros): 20.9 -> "20.9", 90 -> "90". */
export const toInputText = (n: number) => String(Number(n.toFixed(2)));

/** The starting text of every box: the check's values, else the dataset's typical values. */
export function startingValues(features: FeatureInfo[], check?: Readings): Record<string, string> {
  return Object.fromEntries(features.map((f) => [f.key, toInputText(check ? (check[f.key as keyof Readings] as number) : f.default)]));
}

export const STEPS: Record<string, string> = { N: "1", P: "1", K: "1", rainfall: "0.1", temperature: "0.1", humidity: "0.1", ph: "0.1" };

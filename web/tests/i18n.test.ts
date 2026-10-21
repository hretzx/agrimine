import { describe, expect, it } from "vitest";
import en from "@/lib/i18n/dictionaries/en.json";
import mr from "@/lib/i18n/dictionaries/mr.json";
import { format } from "@/lib/i18n/provider";

const placeholders = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();

describe("translations", () => {
  it("English and Marathi have exactly the same keys", () => {
    expect(Object.keys(mr).sort()).toEqual(Object.keys(en).sort());
  });
  it("no message is empty", () => {
    for (const [k, v] of [...Object.entries(en), ...Object.entries(mr)]) expect(v.trim(), k).not.toBe("");
  });
  it("both languages use the same {placeholders}", () => {
    for (const k of Object.keys(en) as (keyof typeof en)[]) expect(placeholders(mr[k]), k).toEqual(placeholders(en[k]));
  });
  it("Marathi text is really Marathi (not a pasted English copy), except names that stay in Latin script", () => {
    const stays = ["app.name", "algo.kmeans.name", "algo.apriori.name"]; // brand and algorithm names
    const same = (Object.keys(en) as (keyof typeof en)[]).filter((k) => en[k] === mr[k]);
    expect(same).toEqual(stays);
  });
  it("Marathi uses Latin digits like the rest of the interface (never a mix of 7 and ७ on one screen)", () => {
    const withDevanagariDigits = Object.entries(mr).filter(([, v]) => /[०-९]/.test(v)).map(([k]) => k);
    expect(withDevanagariDigits).toEqual([]);
  });
  it("every doctor tip the API can send has a message in both languages", () => {
    const tips = ["N", "P", "K", "ph", "temperature", "humidity", "rainfall"].flatMap((f) => ["low", "high"].map((d) => `tip.${f}.${d}`));
    for (const k of tips) { expect(en, k).toHaveProperty([k]); expect(mr, k).toHaveProperty([k]); }
  });
  it("format() fills placeholders and leaves unknown ones visible", () => {
    expect(format("{count} readings", { count: 7 })).toBe("7 readings");
    expect(format("{a} and {b}", { a: 1 })).toBe("1 and {b}");
  });
});

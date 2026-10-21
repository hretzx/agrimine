import type { CropRef, FeatureInfo, Meta } from "@/lib/api/client";
import type { MessageKey } from "@/lib/i18n/dictionaries";
import type { Locale } from "@/lib/i18n/config";
import { cropName, featureLabel } from "@/lib/labels";

/** Soil-health status word and the tone colour used for it everywhere. */
export const STATUS_KEY = { good: "status.good", moderate: "status.moderate", attention: "status.attention" } as const satisfies Record<string, MessageKey>;

/** How close a crop is to the closest crop: the word on its pill and the bar colour. */
export const LEVEL = {
  good: { key: "level.strong", tone: "mint", color: "var(--mint)" },
  moderate: { key: "status.moderate", tone: "butter", color: "var(--butter)" },
  low: { key: "level.consider", tone: "coral", color: "var(--coral)" },
} as const satisfies Record<string, { key: MessageKey; tone: "mint" | "butter" | "coral"; color: string }>;

const WORDS = new Set(["low", "medium", "high", "acidic", "neutral", "alkaline"]);

/** "K=high" -> "Potassium (K) high" / Marathi; "crop=rice" -> "Rice" / "भात". The word (high) is translated by the caller's t(). */
export function patternItem(item: string, meta: Meta | undefined, locale: Locale, word: (w: "low" | "medium" | "high" | "acidic" | "neutral" | "alkaline") => string): string {
  const [name, value = ""] = item.split("=");
  if (name === "crop") {
    const crop = meta?.crops.find((c: CropRef) => c.key === value);
    return crop ? cropName(crop, locale) : value;
  }
  const label = featureLabel(meta?.features, name, locale).replace(/\s*\(.*\)$/, "");
  return `${label} ${WORDS.has(value) ? word(value as never) : value}`;
}

/** A date such as "2026-10-20 13:05" shown as "20 Oct" (or Marathi month names). */
export function shortDate(stamp: string, locale: Locale) {
  const d = new Date(stamp.replace(" ", "T"));
  return Number.isNaN(d.getTime()) ? stamp.slice(0, 10) : d.toLocaleDateString(locale === "mr" ? "mr-IN-u-nu-latn" : "en-GB", { day: "numeric", month: "short" });
}

export const featureRange = (features: FeatureInfo[] | undefined, key: string) => {
  const f = features?.find((x) => x.key === key);
  return f ? { min: f.lo, max: f.hi } : { min: 0, max: 100 };
};

/** 0.9972 -> "99.7%"; a probability that rounds to nothing shows as "0%" instead of "0.0%". */
export const pct = (p: number) => (p >= 0.0005 ? `${(p * 100).toFixed(1)}%` : "0%");

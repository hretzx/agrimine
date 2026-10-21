import type { CropRef, FeatureInfo } from "@/lib/api/client";
import type { Locale } from "@/lib/i18n/config";

/** A crop's display name in the language in use. Keys (rice, jute...) never change; only the label does. */
export const cropName = (crop: Pick<CropRef, "label" | "label_mr">, locale: Locale) => (locale === "mr" ? crop.label_mr : crop.label);

/** A measurement's label in the language in use, from the server's feature registry (GET /api/meta). */
export function featureLabel(features: FeatureInfo[] | undefined, key: string, locale: Locale) {
  const f = features?.find((x) => x.key === key);
  return f ? (locale === "mr" ? f.label_mr : f.label) : key;
}

/** 20.9 with unit "°C" -> "20.9 °C"; N, P, K have no unit; mm, ppm style units are separated by a space. */
export function readingText(value: number, f?: Pick<FeatureInfo, "unit" | "key">) {
  const digits = f && ["ph", "temperature", "humidity"].includes(f.key) ? 1 : 0;
  const n = value.toLocaleString("en", { maximumFractionDigits: digits, minimumFractionDigits: digits });
  return f?.unit ? `${n} ${f.unit}` : n;
}

/** A range with the unit once, at the end: 20.9 and 26.5 with unit "°C" -> "20.9–26.5 °C"; N, P, K -> "63–95". */
export function rangeText(lo: number, hi: number, f?: Pick<FeatureInfo, "unit" | "key">) {
  const digits = f && ["ph", "temperature", "humidity"].includes(f.key) ? 1 : 0;
  const n = (v: number) => v.toLocaleString("en", { maximumFractionDigits: digits, minimumFractionDigits: digits });
  return `${n(lo)}–${n(hi)}${f?.unit ? ` ${f.unit}` : ""}`;
}

/** Which greeting to show for an hour (0-23). */
export const greetingKey = (hour: number): "home.greeting.morning" | "home.greeting.afternoon" | "home.greeting.evening" =>
  hour < 12 ? "home.greeting.morning" : hour < 17 ? "home.greeting.afternoon" : "home.greeting.evening";

/** A crop family's name in the language in use (from GET /api/meta). */
export const familyName = (families: { key: string; label: string; label_mr: string }[] | undefined, key: string, locale: Locale) => {
  const f = families?.find((x) => x.key === key);
  return f ? (locale === "mr" ? f.label_mr : f.label) : key;
};

/** "Rainfall (mm)" / "पाऊस (mm)": the label from the registry plus the unit the registry gives (N, P, K have none). */
export const axisTitle = (features: FeatureInfo[] | undefined, key: string, locale: Locale) => {
  const unit = features?.find((f) => f.key === key)?.unit;
  return `${featureLabel(features, key, locale)}${unit ? ` (${unit})` : ""}`;
};

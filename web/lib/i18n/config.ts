export const LOCALES = ["en", "mr"] as const;
export type Locale = (typeof LOCALES)[number];
export const DEFAULT_LOCALE: Locale = "en";
export const isLocale = (value: string): value is Locale => (LOCALES as readonly string[]).includes(value);

/** The name shown on the language switch (in its own language, so a farmer can always find theirs). */
export const LOCALE_NAMES: Record<Locale, string> = { en: "EN", mr: "मराठी" };

import en from "./dictionaries/en.json";
import mr from "./dictionaries/mr.json";
import type { Locale } from "./config";

/** English is the source of truth: a key that is not in en.json is a TypeScript error everywhere. */
export type MessageKey = keyof typeof en;
export type Dictionary = Record<MessageKey, string>;

export const dictionaries: Record<Locale, Dictionary> = { en, mr };

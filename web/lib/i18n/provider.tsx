"use client";

import { createContext, useContext, useMemo, type ReactNode } from "react";
import type { Locale } from "./config";
import { dictionaries, type MessageKey } from "./dictionaries";

type Translate = (key: MessageKey, values?: Record<string, string | number>) => string;
type I18n = { locale: Locale; t: Translate };

const Ctx = createContext<I18n | null>(null);

/** Fill {placeholders}: format("{count} readings", { count: 7 }) -> "7 readings". */
export function format(template: string, values?: Record<string, string | number>) {
  return values ? template.replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? `{${name}}`)) : template;
}

export function I18nProvider({ locale, children }: { locale: Locale; children: ReactNode }) {
  const value = useMemo<I18n>(() => {
    const dict = dictionaries[locale];
    return { locale, t: (key, values) => format(dict[key] ?? dictionaries.en[key], values) };
  }, [locale]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useI18n(): I18n {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useI18n must be used inside <I18nProvider>");
  return ctx;
}

export const useT = () => useI18n().t;

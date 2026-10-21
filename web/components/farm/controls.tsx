"use client";

import { Moon, Sun } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useSyncExternalStore } from "react";
import { Segmented } from "@/components/ui/segmented";
import { IconButton } from "@/components/ui/icon-button";
import { LOCALES, LOCALE_NAMES, isLocale, type Locale } from "@/lib/i18n/config";
import { useI18n } from "@/lib/i18n/provider";

/** EN / मराठी: changes the first path segment and remembers the choice (the same page in the other language). */
export function LocaleSwitch() {
  const { locale, t } = useI18n();
  const router = useRouter();
  const path = usePathname();
  return (
    <Segmented<Locale>
      label={t("app.name")}
      value={locale}
      options={LOCALES.map((l) => ({ value: l, label: LOCALE_NAMES[l] }))}
      onChange={(next) => {
        localStorage.setItem("lang", next);
        const parts = path.split("/");
        if (isLocale(parts[1])) parts[1] = next;
        router.push(parts.join("/"));
      }}
    />
  );
}

type Theme = "light" | "dark";

// The theme lives on <html data-theme>. Reading it as an external store keeps React in step with whoever changes it.
function subscribeToTheme(onChange: () => void) {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => observer.disconnect();
}
const readTheme = (): Theme => (document.documentElement.dataset.theme === "dark" ? "dark" : "light");

/** Light or dark. The choice is saved; the first paint is handled by the script in the root layout. */
export function ThemeToggle() {
  const { t } = useI18n();
  const theme = useSyncExternalStore(subscribeToTheme, readTheme, () => "light" as Theme);
  return (
    <IconButton
      label={theme === "dark" ? t("theme.light") : t("theme.dark")}
      onClick={() => {
        const next: Theme = theme === "dark" ? "light" : "dark";
        document.documentElement.dataset.theme = next;
        localStorage.setItem("theme", next);
      }}
    >
      {theme === "dark" ? <Sun /> : <Moon />}
    </IconButton>
  );
}

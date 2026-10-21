"use client";

import { AnimatePresence, motion, useCalm } from "@/components/motion";
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
  const calm = useCalm();
  return (
    <IconButton
      label={theme === "dark" ? t("theme.light") : t("theme.dark")}
      onClick={(event) => {
        const next: Theme = theme === "dark" ? "light" : "dark";
        const apply = () => { document.documentElement.dataset.theme = next; localStorage.setItem("theme", next); };
        const view = document as Document & { startViewTransition?: (update: () => void) => { ready: Promise<void> } };
        if (calm || !view.startViewTransition) return apply();
        // the new theme is revealed as a circle growing from the button (the browser cross-fades two snapshots of the page)
        const box = (event.currentTarget as HTMLElement).getBoundingClientRect();
        const x = box.left + box.width / 2, y = box.top + box.height / 2;
        const radius = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
        const transition = view.startViewTransition(apply);
        transition.ready.then(() => document.documentElement.animate(
          { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${radius}px at ${x}px ${y}px)`] },
          { duration: 600, easing: "cubic-bezier(0.22, 1, 0.36, 1)", pseudoElement: "::view-transition-new(root)" },
        )).catch(() => {});
      }}
    >
      {/* the icon turns into the other one */}
      <AnimatePresence mode="wait" initial={false}>
        <motion.span key={theme} className="grid place-items-center [&>svg]:size-[1.05rem]" initial={calm ? false : { rotate: -90, scale: 0.4, opacity: 0 }} animate={{ rotate: 0, scale: 1, opacity: 1 }} exit={calm ? undefined : { rotate: 90, scale: 0.4, opacity: 0 }} transition={{ duration: 0.18 }}>
          {theme === "dark" ? <Sun /> : <Moon />}
        </motion.span>
      </AnimatePresence>
    </IconButton>
  );
}

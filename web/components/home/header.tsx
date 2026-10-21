"use client";

import { Plus } from "lucide-react";
import { useSyncExternalStore, type ReactNode } from "react";
import { LocaleSwitch, ThemeToggle } from "@/components/farm/controls";
import { ButtonLink } from "@/components/ui/button";
import { useI18n } from "@/lib/i18n/provider";
import { greetingKey } from "@/lib/labels";

const subscribe = () => () => {};
/** The hour on the visitor's own clock; the server (build) render uses -1, which shows the neutral morning greeting. */
const useHour = () => useSyncExternalStore(subscribe, () => new Date().getHours(), () => 9);

/** Page title + subtitle on the left; language, theme and "New soil check" on the right. */
export function PageHeader({ title, subtitle }: { title: ReactNode; subtitle?: ReactNode }) {
  const { t, locale } = useI18n();
  return (
    <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
      <div className="min-w-0">
        <h1 className="text-[1.4rem] font-semibold sm:text-[1.6rem] leading-tight tracking-tight" suppressHydrationWarning>{title}</h1>
        {subtitle && <p className="mt-0.5 text-sm text-ink-3">{subtitle}</p>}
      </div>
      <div className="flex shrink-0 items-center gap-2.5">
        <LocaleSwitch />
        <ThemeToggle />
        <ButtonLink href={`/${locale}/check/`}><Plus className="size-4" />{t("action.newCheck")}</ButtonLink>
      </div>
    </div>
  );
}

export function GreetingHeader() {
  const { t } = useI18n();
  return <PageHeader title={t(greetingKey(useHour()))} subtitle={t("home.sub")} />;
}

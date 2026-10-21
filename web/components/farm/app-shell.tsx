"use client";

import { Suspense, type ReactNode } from "react";
import { SidebarContent } from "@/components/home/sidebar-content";
import { STATUS_KEY } from "@/components/home/format";
import { STATUS_TONE } from "@/components/ui/badge";
import { useCurrentCheck, useDoctor, useRecommendation } from "@/lib/data";
import { useI18n } from "@/lib/i18n/provider";
import { Sidebar, type NavId } from "./sidebar";

/**
 * The Crop Doctor chip in the sidebar means one thing: the overall soil health of the RECOMMENDED crop for the check you are
 * looking at. It is absent when nothing is saved yet (there is nothing to judge).
 */
function Frame({ active, children }: { active: NavId; children: ReactNode }) {
  const { t } = useI18n();
  const { check } = useCurrentCheck();
  const best = useRecommendation(check?.values).data?.best.key;
  const overall = useDoctor(check?.values, best).data?.overall;
  const badges = overall ? { doctor: { text: t(STATUS_KEY[overall]), tone: STATUS_TONE[overall] } } : {};
  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <a href="#main" data-testid="skip-link" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-full focus:bg-brand focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-on-brand focus:shadow-lg">{t("a11y.skip")}</a>
      <Sidebar active={active} badges={badges}><SidebarContent /></Sidebar>
      <main id="main" tabIndex={-1} className="min-w-0 flex-1 px-3.5 py-4 outline-none sm:px-[1.625rem] sm:py-[1.375rem]">{children}</main>
    </div>
  );
}

/**
 * Sidebar + page area, the frame of every page. The Suspense boundary is required because the frame reads the address bar
 * (?check=) and a static export must render everything above that read without it.
 */
export function AppShell({ active, children }: { active: NavId; children: ReactNode }) {
  return (
    <Suspense fallback={null}>
      <Frame active={active}>{children}</Frame>
    </Suspense>
  );
}

"use client";

import { usePathname } from "next/navigation";
import { Suspense, type ReactNode } from "react";
import { SidebarContent } from "@/components/home/sidebar-content";
import { STATUS_KEY } from "@/components/home/format";
import { Page } from "@/components/motion";
import { STATUS_TONE } from "@/components/ui/badge";
import { useCurrentCheck, useDoctor, useRecommendation } from "@/lib/data";
import { useI18n } from "@/lib/i18n/provider";
import { Sidebar, type NavId } from "./sidebar";

/** Which sidebar item a page belongs to, from its address (/en/teachers/id3/ -> teachers). The check form and the list of checks belong to Home. */
export function activeFor(pathname: string): NavId {
  const section = pathname.split("/").filter(Boolean)[1] ?? "";
  return ({ grow: "grow", doctor: "doctor", "plan-b": "planb", teachers: "teachers" } as Record<string, NavId>)[section] ?? "home";
}

/**
 * The Crop Doctor chip in the sidebar means one thing: the overall soil health of the RECOMMENDED crop for the check you are
 * looking at. It is absent when nothing is saved yet (there is nothing to judge).
 */
function Frame({ children }: { children: ReactNode }) {
  const { t } = useI18n();
  const pathname = usePathname();
  const { check } = useCurrentCheck();
  const best = useRecommendation(check?.values).data?.best.key;
  const overall = useDoctor(check?.values, best).data?.overall;
  const badges = overall ? { doctor: { text: t(STATUS_KEY[overall]), tone: STATUS_TONE[overall] } } : {};
  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <a href="#main" data-testid="skip-link" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-full focus:bg-brand focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-on-brand focus:shadow-lg">{t("a11y.skip")}</a>
      <Sidebar active={activeFor(pathname)} badges={badges}><SidebarContent /></Sidebar>
      <main id="main" tabIndex={-1} className="min-w-0 flex-1 px-3.5 py-4 outline-none sm:px-[1.625rem] sm:py-[1.375rem]">
        <Page key={pathname}>{children}</Page>
      </main>
    </div>
  );
}

/**
 * Sidebar + page area, the frame of every page. It lives in the layout, so the sidebar stays mounted while you move between pages
 * (its active pill glides to the new item) and only the page content changes. The Suspense boundary is required because the frame
 * reads the address bar (?check=) and a static export must render everything above that read without it.
 * The component gallery (/dev/...) draws its own frame.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  if (pathname.includes("/dev/")) return <>{children}</>;
  return (
    <Suspense fallback={null}>
      <Frame>{children}</Frame>
    </Suspense>
  );
}

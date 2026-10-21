"use client";

import { ChevronDown, GraduationCap, Home, ShieldCheck, Sprout, Stethoscope } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Badge, type Tone } from "@/components/ui/badge";
import { cn } from "@/lib/cn";
import { useCurrentCheck, withCheck } from "@/lib/data";
import { useI18n } from "@/lib/i18n/provider";
import type { MessageKey } from "@/lib/i18n/dictionaries";

export type NavId = "home" | "grow" | "doctor" | "planb" | "teachers";

const ITEMS: { id: NavId; label: MessageKey; href: string; icon: ReactNode }[] = [
  { id: "home", label: "nav.home", href: "", icon: <Home /> },
  { id: "grow", label: "nav.grow", href: "grow/", icon: <Sprout /> },
  { id: "doctor", label: "nav.doctor", href: "doctor/", icon: <Stethoscope /> },
  { id: "planb", label: "nav.planb", href: "plan-b/", icon: <ShieldCheck /> },
  { id: "teachers", label: "nav.teachers", href: "teachers/", icon: <GraduationCap /> },
];

/**
 * The left column, top to bottom: brand, the navigation (+ `children`, the current and recent checks) in a region that scrolls
 * when the window is short, and the landscape with the profile bar on it. The landscape has its OWN space at the bottom: it
 * grows to fill spare height and never goes below 9.5rem, and the scrolling part is squeezed above it, so text is never drawn
 * on top of the picture. `badges` puts a small chip on a nav item (Crop Doctor's soil-health status).
 */
export function Sidebar({ active, badges = {}, children }: { active: NavId; badges?: Partial<Record<NavId, { text: string; tone: Tone }>>; children?: ReactNode }) {
  const { t, locale } = useI18n();
  const tabs = useRef<HTMLElement>(null);
  useEffect(() => {                               // phone: the tab row scrolls sideways, so start with the current page's tab in view
    const row = tabs.current, on = row?.querySelector<HTMLElement>("[aria-current=page]");
    if (row && on) row.scrollLeft = on.offsetLeft - (row.clientWidth - on.offsetWidth) / 2;
  }, [active, badges.doctor?.text]);          // the Crop Doctor chip arrives later and widens the row: centre again

  const [open, setOpen] = useState(false);       // phone only: the current and recent checks fold away under the links
  const { explicitId } = useCurrentCheck();      // moving to another page keeps the check you are looking at
  return (
    <div className="w-full shrink-0 border-b border-line bg-side md:w-[16.75rem] md:border-b-0 md:border-r">
    <aside className="flex flex-col px-3.5 pt-[1.1rem] md:sticky md:top-0 md:h-screen md:overflow-hidden">
      <div className="flex items-center gap-2.5 px-2 pb-4">
        <span className="grid size-[2.1rem] place-items-center rounded-[0.65rem] bg-gradient-to-br from-[#0b1f17] to-[#058a5a] text-white shadow-[inset_0_1px_0_rgb(255_255_255/.25),0_4px_12px_-2px_rgb(5_138_90/.55)] [&>svg]:size-[1.1rem]">
          <Sprout />
        </span>
        <div className="leading-tight">
          <p className="text-[1.1rem] font-bold tracking-tight">{t("app.name")}</p>
          <p className="mt-0.5 whitespace-nowrap text-[0.65rem] font-medium text-ink-3">{t("app.tagline")}</p>
        </div>
      </div>

      <div
        tabIndex={0}
        role="region"
        aria-label={t("nav.farm")}
        data-testid="side-scroll"
        className="min-h-0 flex-[0_1_auto] pb-3 outline-none md:overflow-y-auto md:pb-5 [mask-image:linear-gradient(to_bottom,#000_calc(100%-1.25rem),transparent)] [scrollbar-width:none] focus-visible:rounded-xl focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-brand"
      >
        <p className="hidden px-2.5 pb-1 pt-1 text-[0.65rem] md:block font-bold uppercase tracking-[0.09em] text-ink-3">{t("nav.farm")}</p>
        <nav ref={tabs} aria-label={t("nav.farm")} data-testid="nav-tabs" className="relative flex gap-1 overflow-x-auto overscroll-x-contain [scrollbar-width:none] md:flex-col md:gap-0.5 md:overflow-visible">
          {ITEMS.map((item) => {
            const on = item.id === active;
            const badge = badges[item.id];
            return (
              <Link
                key={item.id}
                href={withCheck(`/${locale}/${item.href}`, explicitId)}
                aria-current={on ? "page" : undefined}
                className={cn(
                  "flex h-11 shrink-0 items-center gap-3 md:h-8 rounded-xl px-3 text-[0.85rem] font-medium text-ink-2 outline-none transition [&>svg]:size-[1.05rem]", // one fixed height: a chip must never push the rows below it
                  "focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand",
                  on ? "bg-nav-on font-semibold text-nav-on-ink shadow-[inset_0_0_0_1px_rgb(255_255_255/.4),0_6px_14px_-8px_rgb(14_59_34/.45)]" : "hover:bg-inset",
                )}
              >
                {item.icon}
                <span>{t(item.label)}</span>
                {badge && <Badge tone={badge.tone} className={cn("ml-auto", on && "bg-black/10 text-nav-on-ink")}>{badge.text}</Badge>}  {/* on the pale active pill a tinted chip would vanish */}
              </Link>
            );
          })}
        </nav>
        <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} aria-controls="side-checks" data-testid="side-checks-toggle"
                className="mt-1 flex h-11 w-full md:h-9 items-center justify-between rounded-xl px-3 text-[0.8rem] font-semibold text-ink-2 outline-none hover:bg-inset focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand md:hidden">
          {t("check.current")} / {t("check.recent")}<ChevronDown className={cn("size-4 transition", open && "rotate-180")} aria-hidden="true" />
        </button>
        <div id="side-checks" className={cn("md:block", open ? "block" : "hidden")}>{children}</div>
      </div>

      {/* The landscape: a transparent PNG (day and night) anchored to the bottom of its own space, with the profile bar on it. */}
      <div data-testid="side-art" className="relative -mx-3.5 hidden min-h-[9.5rem] flex-1 overflow-hidden md:block">
        {/* a short window crops the picture at the top: fade that cut into the sidebar instead of leaving a hard line */}
        <div aria-hidden="true" className="pointer-events-none absolute inset-0 [mask-image:linear-gradient(to_bottom,transparent,#000_2.5rem)]">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/art/landscape.png" alt="" className="absolute bottom-0 left-0 w-full select-none dark:hidden" />
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/art/landscape-night.png" alt="" className="absolute bottom-0 left-0 hidden w-full select-none dark:block" />
        </div>
        <div className="absolute inset-x-3.5 bottom-3"><ProfileBar /></div>
      </div>
    </aside>
    </div>
  );
}

/** The profile bar: avatar with an online dot, name and one line. (No button: there is no profile page to open yet.) */
export function ProfileBar() {
  const t = useI18n().t;
  return (
    <div data-testid="profile" className="relative z-[2] flex items-center gap-2.5 rounded-2xl bg-glass px-2.5 py-2 shadow-[inset_0_1px_0_rgb(255_255_255/.5),0_0_0_1px_var(--line),0_10px_24px_-12px_rgb(0_0_0/.35)] backdrop-blur-md">
      <span className="relative grid size-9 place-items-center rounded-full bg-gradient-to-br from-mint to-sky text-sm font-bold text-white shadow-[0_0_0_2px_var(--card),0_0_0_3.5px_rgb(79_201_138/.65)]">
        F
        <i className="absolute -bottom-px -right-px size-[0.7rem] rounded-full bg-mint shadow-[0_0_0_2px_var(--card)]" />
      </span>
      <div className="min-w-0 leading-tight">
        <p className="text-[0.82rem] font-semibold">{t("profile.farmer")}</p>
        <p className="text-[0.68rem] text-ink-3">{t("profile.field")} · {t("dev.readings", { count: 7 })}</p>
      </div>
    </div>
  );
}

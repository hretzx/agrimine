"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowRight, Pencil } from "lucide-react";
import { CropGlyph } from "@/components/farm/crop-glyph";
import { Badge } from "@/components/ui/badge";
import { IconButton } from "@/components/ui/icon-button";
import { Track } from "@/components/ui/track";
import type { CheckOut } from "@/lib/api/client";
import { useCurrentCheck, useMeta, useRecentChecks, withCheck } from "@/lib/data";
import { useI18n } from "@/lib/i18n/provider";
import { cropName } from "@/lib/labels";
import { featureRange, shortDate } from "./format";

const Section = ({ children }: { children: React.ReactNode }) => (
  <p className="flex items-center px-2.5 pb-1 pt-3 text-[0.65rem] font-bold uppercase tracking-[0.09em] text-ink-3">{children}</p>
);

/** The sidebar's middle: the check you are looking at, and the newest checks (each one opens Home for that check). */
export function SidebarContent() {
  const { t, locale } = useI18n();
  const path = usePathname();
  const meta = useMeta().data;
  const { check, explicitId } = useCurrentCheck();
  const recent = useRecentChecks(4).data ?? [];
  // Switching check keeps you on the page you are on (Crop Doctor stays Crop Doctor); from the form or the list it opens Home.
  const stays = !/\/(check|checks|dev)\//.test(path) && path.replace(/\/$/, "") !== "";
  const hrefFor = (id: number) => `${stays ? path : `/${locale}/`}?check=${id}`;
  const label = (c: CheckOut) => (c.predicted_crop ? cropName(c.predicted_crop, locale) : t("status.pending"));
  return (
    <>
      {check && (
        <>
          <Section>
            {t("check.current")}
            <Badge tone={check.status === "predicted" ? "mint" : "butter"} className="ml-auto normal-case tracking-normal">{check.status === "predicted" ? t("status.predicted") : t("status.pending")}</Badge>
          </Section>
          <div className="mx-0.5 rounded-tile bg-inset p-3 shadow-[inset_0_0_0_1px_var(--line-2)]" data-testid="current-check">
            <div className="mb-2 flex items-center gap-2.5">
              {check.predicted_crop && <CropGlyph crop={check.predicted_crop.key} size={38} />}
              <div className="min-w-0 leading-tight">
                <p className="truncate text-[0.82rem] font-semibold">{label(check)}{check.probability != null && ` · ${(check.probability * 100).toFixed(1)}%`}</p>
                <p className="text-[0.7rem] text-ink-3">#{check.id} · <span data-testid="date">{shortDate(check.created_at, locale)}</span></p>
              </div>
              <Link href={`/${locale}/check/`} aria-label={t("action.newCheck")} className="ml-auto"><IconButton label={t("action.newCheck")} className="size-10 md:size-7"><Pencil /></IconButton></Link>
            </div>
            {(["N", "P", "K", "ph"] as const).map((key) => {
              const { min, max } = featureRange(meta?.features, key);
              return (
                <div key={key} className="mt-1.5 grid grid-cols-[1.5rem_1fr] items-center gap-2 text-[0.68rem] font-semibold text-ink-3">
                  <span>{key === "ph" ? "pH" : key}</span>
                  <Track hatch value={((check.values[key] - min) / (max - min)) * 100} label={`${key}: ${check.values[key]}`} className="[&>div]:h-1.5" />
                </div>
              );
            })}
          </div>
        </>
      )}
      {recent.length > 0 && (
        <>
          <Section>{t("check.recent")}</Section>
          <ul className="mx-0.5 flex flex-col gap-px" data-testid="recent-checks">
            {recent.map((c) => (
              <li key={c.id}>
                <Link href={hrefFor(c.id)} aria-current={(explicitId ?? check?.id) === c.id ? "true" : undefined} className="flex items-center gap-2.5 rounded-xl px-2 py-1.5 outline-none hover:bg-inset focus-visible:outline-2 focus-visible:outline-brand aria-[current=true]:bg-inset">
                  {c.predicted_crop ? <CropGlyph crop={c.predicted_crop.key} size={30} /> : <span className="size-[1.875rem] rounded-[0.55rem] bg-inset" />}
                  <span className="min-w-0 leading-tight">
                    <span className="block truncate text-[0.78rem] font-semibold">#{c.id} · {label(c)}</span>
                    <span className="block text-[0.68rem] text-ink-3" data-testid="date">{shortDate(c.created_at, locale)}</span>
                  </span>
                  <i title={c.status === "predicted" ? t("status.predicted") : t("check.pendingLabel")} className={`ml-auto size-2 rounded-full ${c.status === "predicted" ? "bg-mint" : "bg-butter"}`} />
                </Link>
              </li>
            ))}
          </ul>
          <Link href={withCheck(`/${locale}/checks/`, explicitId)} className="mx-2.5 mt-1.5 inline-flex items-center gap-1.5 text-xs font-semibold text-mint-ink [&>svg]:size-3.5">{t("check.viewAll")}<ArrowRight /></Link>
        </>
      )}
    </>
  );
}

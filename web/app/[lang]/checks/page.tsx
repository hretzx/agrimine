"use client";

import { ClipboardList } from "lucide-react";
import { Suspense } from "react";
import { CropGlyph } from "@/components/farm/crop-glyph";
import { PageHeader } from "@/components/home/header";
import { pct } from "@/components/home/format";
import { Badge } from "@/components/ui/badge";
import { ButtonLink } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { ErrorState, Loading, NoCheck } from "@/components/ui/states";
import { useRecentChecks } from "@/lib/data";
import { useI18n } from "@/lib/i18n/provider";
import { cropName } from "@/lib/labels";

function List() {
  const { t, locale } = useI18n();
  const checks = useRecentChecks(100);
  if (checks.error) return <ErrorState onRetry={() => checks.mutate()} />;
  if (!checks.data) return <Loading className="h-64" />;
  if (checks.data.length === 0) return <NoCheck />;
  return (
    <Card data-testid="all-checks">
      <CardHeader icon={<ClipboardList />} title={t("checks.title")} subtitle={t("checks.sub")} action={<Badge tone="lavender">{checks.data.length}</Badge>} />
      <ul className="divide-y divide-line">
        {checks.data.map((c) => (
          <li key={c.id} className="grid grid-cols-[2.6rem_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-2 py-2.5 sm:grid-cols-[3.2rem_2.6rem_minmax(0,1fr)_auto_auto_auto] sm:gap-4">
            <span className="hidden text-sm font-bold text-ink-3 sm:block">#{c.id}</span>
            {c.predicted_crop ? <CropGlyph crop={c.predicted_crop.key} size={40} /> : <span className="size-10 rounded-[0.7rem] bg-inset" />}
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold"><span className="text-ink-3 sm:hidden">#{c.id} · </span>{c.predicted_crop ? cropName(c.predicted_crop, locale) : t("status.pending")}</p>
              <p className="text-xs text-ink-3">{t("checks.saved", { d: c.created_at })}</p>
            </div>
            <span className="hidden text-sm font-semibold tabular-nums text-ink-2 sm:block">{c.probability != null ? pct(c.probability) : ""}</span>
            <Badge className="hidden sm:inline-flex" tone={c.status === "predicted" ? "mint" : "butter"}>{c.status === "predicted" ? t("status.predicted") : t("status.pending")}</Badge>
            <ButtonLink href={`/${locale}/?check=${c.id}`} variant="outline" className="px-3.5 py-3 text-xs sm:py-1.5">{t("checks.open")}</ButtonLink>
          </li>
        ))}
      </ul>
    </Card>
  );
}

export default function Checks() {
  const { t, locale } = useI18n();
  return (
    <>
      <PageHeader title={t("checks.title")} subtitle={t("checks.sub")} />
      <Suspense fallback={<Loading className="h-64" />}><List /></Suspense>
      <div className="mt-4"><ButtonLink href={`/${locale}/check/`} variant="outline">{t("action.newCheck")}</ButtonLink></div>
    </>
  );
}

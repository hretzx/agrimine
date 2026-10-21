"use client";

import { ClipboardCheck, Database, Wheat } from "lucide-react";
import { StatCard } from "@/components/farm/stat-card";
import { Badge } from "@/components/ui/badge";
import { useMeta, useRecentChecks } from "@/lib/data";
import { useI18n } from "@/lib/i18n/provider";
import { shortDate } from "./format";

/** Records, crops, saved checks: every number comes from GET /api/meta and the checks list. */
export function Stats() {
  const { t, locale } = useI18n();
  const meta = useMeta().data;
  const last = useRecentChecks(1).data?.[0];
  const dash = "–";
  return (
    <div className="mb-3 grid grid-cols-1 gap-3 sm:grid-cols-3" data-testid="stats">
      <StatCard icon={<Database />} label={t("stat.records")} value={meta ? meta.records.toLocaleString("en") : dash} tint="linear-gradient(160deg,#e9f7e4,#cdebc3)" note={meta && <Badge tone="lavender">{t("stat.recordsNote", { n: meta.features.length })}</Badge>} />
      <StatCard icon={<Wheat />} label={t("stat.crops")} value={meta ? meta.crops.length : dash} tint="linear-gradient(160deg,#fff6d6,#f5df8e)" note={meta && <Badge tone="butter">{t("stat.cropsNote", { n: Math.round(meta.records / meta.crops.length) })}</Badge>} />
      <StatCard icon={<ClipboardCheck />} label={t("stat.checks")} value={meta ? meta.saved_checks.toLocaleString("en") : dash} tint="linear-gradient(160deg,#e4f4fc,#bfe6f6)" note={meta && <Badge tone="sky" data-testid={last ? "date" : undefined}>{last ? t("stat.checksLast", { d: shortDate(last.created_at, locale) }) : t("stat.checksNone")}</Badge>} />
    </div>
  );
}

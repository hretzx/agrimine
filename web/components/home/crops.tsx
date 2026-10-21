"use client";

import { ArrowUpRight, Shield, Stethoscope, Trophy } from "lucide-react";
import Link from "next/link";
import { CropRow } from "@/components/farm/crop-row";
import { Badge, STATUS_TONE } from "@/components/ui/badge";
import { Card, CardHeader } from "@/components/ui/card";
import { Gauge } from "@/components/ui/gauge";
import { ErrorState, Loading, NoCheck } from "@/components/ui/states";
import type { CheckOut, RankedCropT } from "./types";
import { useDoctor, useMeta, useRecommendation, withCheck } from "@/lib/data";
import { useI18n } from "@/lib/i18n/provider";
import { cropName, featureLabel, rangeText, readingText } from "@/lib/labels";
import { featureRange, LEVEL, pct, STATUS_KEY } from "./format";

/** Rows for a list of crops. `first` marks the ranking list (probability shown, rank 1 is "Best choice"); Plan B rows show the match only. */
function crops(rows: RankedCropT[], first: boolean, locale: "en" | "mr", t: ReturnType<typeof useI18n>["t"]) {
  return rows.map((r, i) => {
    const level = LEVEL[r.level];
    return (
      <CropRow
        key={r.crop.key}
        crop={r.crop.key}
        name={cropName(r.crop, locale)}
        subtitle={first ? t("top3.likely", { p: pct(r.probability) }) : t("top3.match")}
        score={r.match}
        tone={first && i === 0 ? "mint" : level.tone}
        color={first && i === 0 ? "var(--mint)" : level.color}
        tag={first && i === 0 ? t("top3.best") : t(level.key)}
      />
    );
  });
}

/** The three crops the model finds most likely (ordered by probability), each with its separate profile-match bar. */
export function TopCrops({ check }: { check?: CheckOut }) {
  const { t, locale } = useI18n();
  const rec = useRecommendation(check?.values);
  return (
    <Card>
      <CardHeader icon={<Trophy />} title={t("top3.title")} subtitle={t("top3.sub")} />
      {!check ? <NoCheck /> : rec.error ? <ErrorState onRetry={() => rec.mutate()} /> : !rec.data ? <Loading className="h-60" /> : <div className="space-y-2.5" data-testid="top3">{crops(rec.data.ranking.slice(0, 3), true, locale, t)}</div>}
    </Card>
  );
}

/** The crops whose conditions are closest, if the main crop does not work out (ordered by profile similarity). */
export function PlanB({ check }: { check?: CheckOut }) {
  const { t, locale } = useI18n();
  const rec = useRecommendation(check?.values);
  return (
    <Card>
      <CardHeader icon={<Shield />} title={t("planb.title")} subtitle={t("planb.sub")} action={<Link href={withCheck(`/${locale}/plan-b/`, check?.id)} aria-label={t("planb.title")} className="grid size-10 sm:size-[2.125rem] place-items-center rounded-full bg-card shadow-[0_0_0_1px_var(--line)] [&>svg]:size-4"><ArrowUpRight /></Link>} />
      {!check ? <NoCheck /> : rec.error ? <ErrorState onRetry={() => rec.mutate()} /> : !rec.data ? <Loading className="h-60" /> : <div className="space-y-2.5" data-testid="planb">{crops(rec.data.similar.slice(0, 3), false, locale, t)}</div>}
    </Card>
  );
}

const NUTRIENTS = ["N", "P", "K", "ph"] as const;

/** Soil nutrients and pH of the check against the range the best crop grows in. */
export function DoctorCard({ check }: { check?: CheckOut }) {
  const { t, locale } = useI18n();
  const meta = useMeta().data;
  const rec = useRecommendation(check?.values);
  const best = rec.data?.best;
  const doctor = useDoctor(check?.values, best?.key);
  const d = doctor.data;
  return (
    <Card>
      <CardHeader
        icon={<Stethoscope />}
        title={t("doctor.title")}
        subtitle={best ? t("doctor.sub", { crop: cropName(best, locale) }) : undefined}
        action={d && <Badge tone={STATUS_TONE[d.overall]}>{t("doctor.overall")} · {t(STATUS_KEY[d.overall])}</Badge>}
      />
      {!check ? <NoCheck /> : doctor.error ? <ErrorState onRetry={() => doctor.mutate()} /> : !d ? <Loading className="h-60" /> : (
        <div data-testid="doctor">
          {d.readings.filter((r) => (NUTRIENTS as readonly string[]).includes(r.feature)).map((r) => {
            const f = meta?.features.find((x) => x.key === r.feature);
            const { min, max } = featureRange(meta?.features, r.feature);
            const name = featureLabel(meta?.features, r.feature, locale);
            return (
              <div key={r.feature} className="grid grid-cols-[6.5rem_1fr_auto] items-center gap-3 border-b border-dashed border-line py-2.5 last:border-0">
                <div>
                  <p className="text-[0.82rem] font-semibold">{name}</p>
                  <p className="text-[0.7rem] text-ink-3">{readingText(r.value, f)} · {rangeText(r.low, r.high, f)}</p>
                </div>
                <Gauge value={r.value} low={r.low} high={r.high} min={min} max={max} status={r.status} label={`${name}: ${t(STATUS_KEY[r.status])}`} />
                <Badge tone={STATUS_TONE[r.status]}>{t(STATUS_KEY[r.status])}</Badge>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

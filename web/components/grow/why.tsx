"use client";

import { CircleHelp, Info } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader } from "@/components/ui/card";
import { ErrorState, Loading } from "@/components/ui/states";
import type { Recommendation } from "@/lib/api/client";
import { useDoctor, useMeta } from "@/lib/data";
import { useI18n } from "@/lib/i18n/provider";
import { cropName, featureLabel, rangeText, readingText } from "@/lib/labels";
import type { Readings } from "@/lib/api/client";

/** The three readings closest to what the best crop grows in, each shown against that crop's usual range. */
export function WhyCard({ rec, readings }: { rec: Recommendation; readings: Readings }) {
  const { t, locale } = useI18n();
  const meta = useMeta().data;
  const doctor = useDoctor(readings, rec.best.key);
  const report = doctor.data;
  return (
    <Card data-testid="why">
      <CardHeader icon={<CircleHelp />} title={t("grow.why.title", { crop: cropName(rec.best, locale) })} subtitle={t("grow.why.sub")} />
      {doctor.error ? <ErrorState onRetry={() => doctor.mutate()} /> : !report ? <Loading className="h-32" /> : (
        <div>
          {rec.reasons.map((key) => {
            const r = report.readings.find((x) => x.feature === key)!;
            const f = meta?.features.find((x) => x.key === key);
            const inside = r.status === "good";
            return (
              <div key={key} className="flex items-center justify-between gap-3 border-b border-dashed border-line py-2.5 last:border-0">
                <div>
                  <p className="text-sm font-semibold">{featureLabel(meta?.features, key, locale)}</p>
                  <p className="text-xs text-ink-3">{readingText(r.value, f)} · {t("doctor.usual", { range: rangeText(r.low, r.high, f) })}</p>
                </div>
                <Badge tone={inside ? "mint" : "butter"}>{inside ? t("grow.why.inside") : t("grow.why.near")}</Badge>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

export function HowCard({ body, title }: { body: string; title: string }) {
  return (
    <Card>
      <CardHeader icon={<Info />} title={title} />
      <p className="text-[0.82rem] leading-relaxed text-ink-3">{body}</p>
    </Card>
  );
}

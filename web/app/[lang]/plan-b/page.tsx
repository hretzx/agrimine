"use client";

import { Suspense, useState } from "react";
import { AppShell } from "@/components/farm/app-shell";
import { CropSelect } from "@/components/farm/crop-select";
import { CropGlyph } from "@/components/farm/crop-glyph";
import { ReadingsEditor } from "@/components/farm/readings-editor";
import { CompareTable } from "@/components/grow/compare";
import { PageHeader } from "@/components/home/header";
import { LEVEL, STATUS_KEY } from "@/components/home/format";
import { Badge, STATUS_TONE } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { ErrorState, Loading } from "@/components/ui/states";
import { Track } from "@/components/ui/track";
import type { PlanBResponse } from "@/lib/api/client";
import { useMeta, usePlanB, useRecommendation } from "@/lib/data";
import { useI18n } from "@/lib/i18n/provider";
import { cropName, featureLabel, rangeText } from "@/lib/labels";
import { useReadings } from "@/lib/use-readings";

const VERDICT = { good: { key: "planb.verdict.good", box: "bg-mint/16 text-mint-ink" }, moderate: { key: "planb.verdict.moderate", box: "bg-butter/24 text-butter-ink" }, low: { key: "planb.verdict.low", box: "bg-coral/16 text-coral-ink" } } as const;

function Alternative({ alt }: { alt: PlanBResponse["alternatives"][number] }) {
  const { t, locale } = useI18n();
  const meta = useMeta().data;
  const level = LEVEL[alt.level];
  const fits = alt.needs.filter((n) => n.status === "good").length;
  return (
    <Card data-testid={`alt-${alt.crop.key}`}>
      <div className="flex items-center gap-3">
        <CropGlyph crop={alt.crop.key} size={48} />
        <div className="min-w-0 flex-1">
          <p className="text-base font-semibold">{cropName(alt.crop, locale)}</p>
          <Track value={alt.match} label={`${cropName(alt.crop, locale)}: ${Math.round(alt.match)}`} color={level.color} className="mt-1.5 [&>div]:h-1.5" />
        </div>
        <Badge tone={level.tone}>{t(level.key)}</Badge>
        <span className="grid min-w-[3.5rem] place-items-center rounded-xl bg-card px-2.5 py-2 text-base font-semibold tabular-nums shadow-[0_0_0_1px_var(--line),0_2px_6px_-2px_rgb(0_0_0/.18)]">{Math.round(alt.match)}</span>
      </div>
      <p className="mb-2 mt-4 flex items-center justify-between text-xs font-semibold text-ink-3"><span>{t("planb.needs")}</span><span>{t("planb.fits", { n: fits })}</span></p>
      <ul className="divide-y divide-dashed divide-line text-[0.82rem]">
        {alt.needs.map((n) => {
          const f = meta?.features.find((x) => x.key === n.feature);
          return (
            <li key={n.feature} className="flex items-center justify-between gap-3 py-1.5">
              <span className="text-ink-2">{featureLabel(meta?.features, n.feature, locale)}</span>
              <span className="flex items-center gap-2 font-semibold tabular-nums">{rangeText(n.low, n.high, f)}<Badge tone={STATUS_TONE[n.status]}>{t(STATUS_KEY[n.status])}</Badge></span>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

function PlanBBody() {
  const { t, locale } = useI18n();
  const state = useReadings();
  const rec = useRecommendation(state.readings);
  const [chosen, setChosen] = useState<string | null>(null);
  const preferred = chosen ?? rec.data?.best.key; // until you choose, start from the recommended crop
  const plan = usePlanB(state.readings, preferred);
  if (state.error) return <ErrorState />;
  if (!state.ready) return <Loading className="h-96" />;
  const data = plan.data;
  const v = data && VERDICT[data.level];
  const preferredName = data ? cropName(data.preferred, locale) : "";
  return (
    <div className="space-y-3">
      <ReadingsEditor state={state} />
      <Card className="py-3.5"><CropSelect label={t("planb.crop")} value={preferred ?? ""} onChange={setChosen} /></Card>
      {plan.error ? <ErrorState onRetry={() => plan.mutate()} /> : !data || !state.readings ? (state.valid ? <Loading className="h-96" /> : null) : (
        <div className={`space-y-3 transition-opacity ${state.settling ? "opacity-60" : ""}`} aria-busy={state.settling}>
          <div className={`rounded-card px-5 py-4 ${v!.box}`} role="status" data-testid="verdict" data-level={data.level}>
            <p className="text-base font-semibold">{t(v!.key, { crop: preferredName })}</p>
            <p className="mt-1 text-xs">{t("planb.scores", { crop: preferredName, a: Math.round(data.preferred_match), best: cropName(data.best_crop, locale), b: Math.round(data.best_match) })}</p>
          </div>
          <div className="grid grid-cols-1 items-start gap-3 md:grid-cols-3">{data.alternatives.map((a) => <Alternative key={a.crop.key} alt={a} />)}</div>
          <CompareTable testId="planb-compare" readings={state.readings} crops={[data.preferred.key, ...data.alternatives.map((a) => a.crop.key)]} title={t("planb.compare")} subtitle={t("planb.compare.sub")} />
        </div>
      )}
    </div>
  );
}

export default function PlanB() {
  const { t } = useI18n();
  return (
    <AppShell active="planb">
      <PageHeader title={t("planb.page.title")} subtitle={t("planb.page.sub")} />
      <Suspense fallback={<Loading className="h-96" />}>
        <PlanBBody />
      </Suspense>
    </AppShell>
  );
}

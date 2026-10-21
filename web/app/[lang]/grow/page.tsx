"use client";

import { Suspense, useState } from "react";
import { AppShell } from "@/components/farm/app-shell";
import { ReadingsEditor } from "@/components/farm/readings-editor";
import { CompareTable } from "@/components/grow/compare";
import { RankingCard } from "@/components/grow/ranking";
import { MatchCard, RecommendedCard, TreeCard } from "@/components/grow/recommended";
import { HowCard, WhyCard } from "@/components/grow/why";
import { PageHeader } from "@/components/home/header";
import { ErrorState, Loading } from "@/components/ui/states";
import { useRecommendation } from "@/lib/data";
import { useI18n } from "@/lib/i18n/provider";
import { cropName } from "@/lib/labels";
import { useReadings } from "@/lib/use-readings";

function GrowBody() {
  const { t, locale } = useI18n();
  const state = useReadings();
  const rec = useRecommendation(state.readings);
  const [picked, setPicked] = useState<string[] | null>(null);
  if (state.error) return <ErrorState />;
  if (!state.ready) return <Loading className="h-96" />;
  const data = rec.data;
  const compare = picked ?? (data ? data.ranking.slice(0, 3).map((r) => r.crop.key) : []);
  return (
    <div className="space-y-3">
      <ReadingsEditor state={state} />
      {rec.error ? <ErrorState onRetry={() => rec.mutate()} /> : !data || !state.readings ? (state.valid ? <Loading className="h-80" /> : null) : (
        <div className={`space-y-3 transition-opacity ${state.settling ? "opacity-60" : ""}`} aria-busy={state.settling}>
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1.35fr_1fr_1fr]">
            <RecommendedCard rec={data} />
            <TreeCard rec={data} />
            <MatchCard rec={data} />
          </div>
          <div className="grid grid-cols-1 items-start gap-3 lg:grid-cols-[1.25fr_1fr]">
            <RankingCard rec={data} />
            <div className="space-y-3">
              <WhyCard rec={data} readings={state.readings} />
              <HowCard title={t("grow.how.title")} body={t("grow.how.body")} />
            </div>
          </div>
          <CompareTable testId="compare" readings={state.readings} crops={compare} onChange={setPicked} title={t("grow.compare.title")} subtitle={t("grow.compare.sub")} />
          <span className="sr-only" aria-live="polite">{cropName(data.best, locale)}</span>
        </div>
      )}
    </div>
  );
}

export default function Grow() {
  const { t } = useI18n();
  return (
    <AppShell active="grow">
      <PageHeader title={t("grow.title")} subtitle={t("grow.sub")} />
      <Suspense fallback={<Loading className="h-96" />}>
        <GrowBody />
      </Suspense>
    </AppShell>
  );
}

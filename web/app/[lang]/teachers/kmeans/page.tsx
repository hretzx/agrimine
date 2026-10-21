"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Suspense, useState } from "react";
import { AppShell } from "@/components/farm/app-shell";
import { ReadingsEditor } from "@/components/farm/readings-editor";
import { HowCard } from "@/components/grow/why";
import { PageHeader } from "@/components/home/header";
import { KChoose, KControls, KCrops, KMap, KProfiles, KYours } from "@/components/teachers/kmeans";
import { ErrorState, Loading } from "@/components/ui/states";
import { useKMeans, useMeta } from "@/lib/data";
import { useI18n } from "@/lib/i18n/provider";
import { useReadings } from "@/lib/use-readings";

function KMeansBody() {
  const { t } = useI18n();
  const state = useReadings();
  const [k, setK] = useState(4);
  const report = useKMeans(state.readings, k);
  const features = useMeta().data?.features;
  if (state.error) return <ErrorState />;
  if (!state.ready) return <Loading className="h-96" />;
  const data = report.data;
  return (
    <div className="space-y-3">
      <ReadingsEditor state={state} />
      <KControls k={k} setK={setK} report={data?.k === k ? data : undefined} />
      {report.error ? <ErrorState onRetry={() => report.mutate()} /> : !data || !state.readings ? (state.valid ? <Loading className="h-80" /> : null) : (
        <div className={`space-y-3 transition-opacity ${state.settling || data.k !== k ? "opacity-60" : ""}`} aria-busy={state.settling || data.k !== k}>
          <KYours report={data} />
          <KMap report={data} />
          <KProfiles report={data} features={features} />
          <div className="grid grid-cols-1 items-start gap-3 lg:grid-cols-[1fr_1.1fr]">
            <KCrops report={data} />
            <div className="space-y-3">
              <KChoose report={data} />
              <HowCard title={t("km.how.title")} body={t("km.how.body")} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function KMeansPage() {
  const { t, locale } = useI18n();
  return (
    <AppShell active="teachers">
      <Link href={`/${locale}/teachers/`} className="-mt-2 mb-1 inline-flex min-h-10 items-center gap-1.5 text-xs font-semibold text-ink-3 outline-none hover:text-ink focus-visible:outline-2 focus-visible:outline-brand md:mt-0 md:min-h-0">
        <ArrowLeft className="size-3.5" aria-hidden="true" />{t("teachers.back")}
      </Link>
      <PageHeader title={t("km.title")} subtitle={t("km.sub")} />
      <Suspense fallback={<Loading className="h-96" />}>
        <KMeansBody />
      </Suspense>
    </AppShell>
  );
}

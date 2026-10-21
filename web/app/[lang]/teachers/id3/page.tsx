"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Suspense } from "react";
import { ReadingsEditor } from "@/components/farm/readings-editor";
import { HowCard } from "@/components/grow/why";
import { PageHeader } from "@/components/home/header";
import { Id3Accuracy, Id3Alternatives, Id3Answer, Id3Model, Id3Path } from "@/components/teachers/id3";
import { ErrorState, Loading } from "@/components/ui/states";
import { useId3, useMeta } from "@/lib/data";
import { useI18n } from "@/lib/i18n/provider";
import { useReadings } from "@/lib/use-readings";

function Id3Body() {
  const { t } = useI18n();
  const state = useReadings();
  const report = useId3(state.readings);
  const features = useMeta().data?.features;
  if (state.error) return <ErrorState />;
  if (!state.ready) return <Loading className="h-96" />;
  const data = report.data;
  return (
    <div className="space-y-3">
      <ReadingsEditor state={state} />
      {report.error ? <ErrorState onRetry={() => report.mutate()} /> : !data || !state.readings ? (state.valid ? <Loading className="h-80" /> : null) : (
        <div className={`space-y-3 transition-opacity ${state.settling ? "opacity-60" : ""}`} aria-busy={state.settling}>
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1.35fr_1fr]">
            <Id3Answer report={data} />
            <Id3Accuracy report={data} />
          </div>
          <div className="grid grid-cols-1 items-start gap-3 lg:grid-cols-[1.3fr_1fr]">
            <div className="space-y-3">
              <Id3Path report={data} features={features} />
              <Id3Alternatives report={data} />
            </div>
            <div className="space-y-3">
              <HowCard title={t("id3.how.title")} body={t("id3.how.body")} />
              <Id3Model report={data} features={features} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Id3Page() {
  const { t, locale } = useI18n();
  return (
    <>
      <Link href={`/${locale}/teachers/`} className="-mt-2 mb-1 inline-flex min-h-10 items-center gap-1.5 md:mt-0 md:min-h-0 text-xs font-semibold text-ink-3 outline-none hover:text-ink focus-visible:outline-2 focus-visible:outline-brand">
        <ArrowLeft className="size-3.5" aria-hidden="true" />{t("teachers.back")}
      </Link>
      <PageHeader title={t("id3.title")} subtitle={t("id3.sub")} />
      <Suspense fallback={<Loading className="h-96" />}>
        <Id3Body />
      </Suspense>
    </>
  );
}

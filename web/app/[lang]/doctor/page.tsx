"use client";

import { Suspense, useState } from "react";
import { AppShell } from "@/components/farm/app-shell";
import { CropSelect } from "@/components/farm/crop-select";
import { ReadingsEditor } from "@/components/farm/readings-editor";
import { GaugesCard, OverallCard, TipsCard } from "@/components/doctor/report";
import { HowCard } from "@/components/grow/why";
import { PageHeader } from "@/components/home/header";
import { Card } from "@/components/ui/card";
import { ErrorState, Loading } from "@/components/ui/states";
import { useDoctor, useRecommendation } from "@/lib/data";
import { useI18n } from "@/lib/i18n/provider";
import { useReadings } from "@/lib/use-readings";

function DoctorBody() {
  const { t } = useI18n();
  const state = useReadings();
  const rec = useRecommendation(state.readings);
  const [chosen, setChosen] = useState<string | null>(null);
  const crop = chosen ?? rec.data?.best.key; // until you choose, the doctor looks at the crop the model recommends
  const doctor = useDoctor(state.readings, crop);
  if (state.error) return <ErrorState />;
  if (!state.ready) return <Loading className="h-96" />;
  const report = doctor.data;
  return (
    <div className="space-y-3">
      <ReadingsEditor state={state} />
      <Card className="py-3.5">
        <CropSelect label={t("doctor.crop")} value={crop ?? ""} onChange={setChosen} mark={rec.data?.best.key} markText={t("doctor.crop.recommended")} />
      </Card>
      {doctor.error || rec.error ? <ErrorState onRetry={() => { void doctor.mutate(); void rec.mutate(); }} /> : !report || !state.readings ? (state.valid ? <Loading className="h-96" /> : null) : (
        <div className={`space-y-3 transition-opacity ${state.settling ? "opacity-60" : ""}`} aria-busy={state.settling}>
          <div className="grid grid-cols-1 items-start gap-3 lg:grid-cols-[1fr_2fr]">
            <OverallCard report={report} checkId={state.check?.id} />
            <div className="space-y-3">
              <GaugesCard report={report} group="nutrients" />
              <GaugesCard report={report} group="weather" />
            </div>
          </div>
          <TipsCard report={report} />
          <HowCard title={t("doctor.how.title")} body={t("doctor.how.body")} />
        </div>
      )}
    </div>
  );
}

export default function Doctor() {
  const { t } = useI18n();
  return (
    <AppShell active="doctor">
      <PageHeader title={t("doctor.page.title")} subtitle={t("doctor.page.sub")} />
      <Suspense fallback={<Loading className="h-96" />}>
        <DoctorBody />
      </Suspense>
    </AppShell>
  );
}

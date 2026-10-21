"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Suspense, useState } from "react";
import { AppShell } from "@/components/farm/app-shell";
import { HowCard } from "@/components/grow/why";
import { PageHeader } from "@/components/home/header";
import { AprioriControls, AprioriLift, AprioriStats, AprioriTable, AprioriTop } from "@/components/teachers/apriori";
import { Card } from "@/components/ui/card";
import { ErrorState, Loading } from "@/components/ui/states";
import type { AprioriQuery } from "@/lib/api/client";
import { useApriori, useMeta } from "@/lib/data";
import { useI18n } from "@/lib/i18n/provider";

const DEFAULTS: AprioriQuery = { minSupport: 0.01, minConfidence: 0.6, maxLen: 5, crop: "", onlyCrop: true };

function AprioriBody() {
  const { t } = useI18n();
  const [q, setQ] = useState(DEFAULTS);
  const report = useApriori(q);
  const meta = useMeta().data;
  const data = report.data;
  return (
    <div className="space-y-3">
      <AprioriControls q={q} set={setQ} meta={meta} />
      {report.error ? <ErrorState onRetry={() => report.mutate()} /> : !data ? <Loading className="h-80" /> : (
        <div className="space-y-3" aria-busy={report.isValidating}>
          <AprioriStats report={data} />
          {data.rules.length === 0 ? (
            <Card data-testid="apr-none"><p className="text-sm text-ink-3">{t("apr.none")}</p></Card>
          ) : (
            <>
              <AprioriTop report={data} meta={meta} />
              <div className="grid grid-cols-1 items-start gap-3 lg:grid-cols-[1.35fr_1fr]">
                <AprioriTable report={data} meta={meta} />
                <div className="space-y-3">
                  <AprioriLift report={data} meta={meta} />
                  <HowCard title={t("apr.how.title")} body={t("apr.how.body")} />
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default function AprioriPage() {
  const { t, locale } = useI18n();
  return (
    <AppShell active="teachers">
      <Link href={`/${locale}/teachers/`} className="-mt-2 mb-1 inline-flex min-h-10 items-center gap-1.5 text-xs font-semibold text-ink-3 outline-none hover:text-ink focus-visible:outline-2 focus-visible:outline-brand md:mt-0 md:min-h-0">
        <ArrowLeft className="size-3.5" aria-hidden="true" />{t("teachers.back")}
      </Link>
      <PageHeader title={t("apr.title")} subtitle={t("apr.sub")} />
      <Suspense fallback={<Loading className="h-96" />}>
        <AprioriBody />
      </Suspense>
    </AppShell>
  );
}

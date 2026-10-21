"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Suspense, useState } from "react";
import { HowCard } from "@/components/grow/why";
import { PageHeader } from "@/components/home/header";
import { Dendrogram, Diana, HierClusters, HierControls } from "@/components/teachers/hierarchical";
import { ErrorState, Loading } from "@/components/ui/states";
import { useHierarchical } from "@/lib/data";
import { useI18n } from "@/lib/i18n/provider";

function HierBody() {
  const { t } = useI18n();
  const [method, setMethod] = useState("ward");
  const [k, setK] = useState(4);
  const report = useHierarchical(method, k);
  const data = report.data;
  const fresh = data?.method === method && data.k === k;
  return (
    <div className="space-y-3">
      <HierControls method={method} setMethod={setMethod} k={k} setK={setK} report={fresh ? data : undefined} />
      {report.error ? <ErrorState onRetry={() => report.mutate()} /> : !data ? <Loading className="h-80" /> : (
        <div className={`space-y-3 transition-opacity ${fresh ? "" : "opacity-60"}`} aria-busy={!fresh}>
          <Dendrogram report={data} />
          <HierClusters report={data} />
          <div className="grid grid-cols-1 items-start gap-3 lg:grid-cols-[1.6fr_1fr]">
            <Diana report={data} />
            <HowCard title={t("hier.how.title")} body={t("hier.how.body")} />
          </div>
        </div>
      )}
    </div>
  );
}

export default function HierarchicalPage() {
  const { t, locale } = useI18n();
  return (
    <>
      <Link href={`/${locale}/teachers/`} className="-mt-2 mb-1 inline-flex min-h-10 items-center gap-1.5 text-xs font-semibold text-ink-3 outline-none hover:text-ink focus-visible:outline-2 focus-visible:outline-brand md:mt-0 md:min-h-0">
        <ArrowLeft className="size-3.5" aria-hidden="true" />{t("teachers.back")}
      </Link>
      <PageHeader title={t("hier.title")} subtitle={t("hier.sub")} />
      <Suspense fallback={<Loading className="h-96" />}>
        <HierBody />
      </Suspense>
    </>
  );
}

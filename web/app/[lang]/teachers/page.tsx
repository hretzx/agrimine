"use client";

import { ExternalLink, FlaskConical, GraduationCap } from "lucide-react";
import Link from "next/link";
import { PageHeader } from "@/components/home/header";
import { AccuracyCard } from "@/components/home/insights";
import { ButtonLink } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { useCurrentCheck, useLab, withCheck } from "@/lib/data";
import { LAB_PAGE, labLink } from "@/lib/lab";
import type { MessageKey } from "@/lib/i18n/dictionaries";
import { useI18n } from "@/lib/i18n/provider";

/** Links into the Streamlit lab on the same check as this page. They read the address, so they live inside the AppShell (its Suspense boundary). */
const PILL = "inline-flex items-center gap-1 whitespace-nowrap rounded-full px-3 py-3 text-xs md:px-2.5 md:py-1 font-semibold shadow-[inset_0_0_0_1px_var(--line)]";

function LabLink({ algo }: { algo: keyof typeof LAB_PAGE }) {
  const { t } = useI18n();
  const { check } = useCurrentCheck();
  const lab = useLab().data;
  if (!lab?.available) {
    return <span data-testid={`lab-${algo}`} aria-disabled="true" title={t("teachers.lab.off")} className={`${PILL} text-ink-3`}>{t("teachers.openLab")}</span>;
  }
  return (
    <a data-testid={`lab-${algo}`} href={labLink(lab.url, LAB_PAGE[algo], check?.id)} target="_blank" rel="noreferrer"
       className={`${PILL} text-brand outline-none hover:bg-inset focus-visible:outline-2 focus-visible:outline-brand`}>
      {t("teachers.openLab")}<ExternalLink className="size-3" aria-hidden="true" />
    </a>
  );
}

function LabHomeLink() {
  const { t } = useI18n();
  const { check } = useCurrentCheck();
  const lab = useLab().data;
  if (!lab) return null;
  if (!lab.available) return <p data-testid="lab-off" className="mt-3 rounded-tile bg-inset px-3 py-2 text-[0.8rem] leading-snug text-ink-2">{t("teachers.lab.off")}</p>;
  return (
    <ButtonLink data-testid="lab-home" href={labLink(lab.url, undefined, check?.id)} target="_blank" rel="noreferrer" variant="ghost" className="mt-3">
      {t("teachers.lab.open")}<ExternalLink className="size-3.5" aria-hidden="true" />
    </ButtonLink>
  );
}

const ALGOS = ["id3", "nb", "kmeans", "hier", "apriori", "fp", "regression", "match"] as const;

/** Algorithms whose page has been ported into this app (the others are in the lab only, for now). */
const PORTED: Partial<Record<(typeof ALGOS)[number], string>> = { id3: "id3", nb: "naive-bayes", kmeans: "kmeans", apriori: "apriori", hier: "hierarchical" };

function WebLink({ algo, page }: { algo: string; page: string }) {
  const { t, locale } = useI18n();
  const { check } = useCurrentCheck();
  return (
    <Link data-testid={`web-${algo}`} href={withCheck(`/${locale}/teachers/${page}/`, check?.id)}
          className={`${PILL} bg-brand text-on-brand outline-none hover:brightness-110 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand`}>
      {t("teachers.openWeb")}
    </Link>
  );
}

export default function Teachers() {
  const { t } = useI18n();
  return (
    <>
      <PageHeader title={t("teachers.title")} subtitle={t("teachers.sub")} />
      <div className="grid grid-cols-1 items-start gap-3 lg:grid-cols-[1.6fr_1fr]">
        <Card data-testid="algos">
          <CardHeader icon={<GraduationCap />} title={t("teachers.algos")} subtitle={t("teachers.algos.sub")} />
          <ul className="divide-y divide-line">
            {ALGOS.map((a) => (
              <li key={a} className="grid grid-cols-1 gap-2 py-3 text-sm md:grid-cols-[14rem_1fr_auto] md:items-center md:gap-4">
                <b className="font-semibold">{t(`algo.${a}.name` as MessageKey)}</b>
                <span className="text-ink-3"><span className="text-xs font-semibold text-ink-2">{t("teachers.used")}: </span>{t(`algo.${a}.use` as MessageKey)}</span>
                <span className="flex items-center gap-1.5">
                  {PORTED[a] && <WebLink algo={a} page={PORTED[a]!} />}
                  {a in LAB_PAGE && <LabLink algo={a as keyof typeof LAB_PAGE} />}
                </span>
              </li>
            ))}
          </ul>
        </Card>
        <div className="space-y-3">
          <AccuracyCard />
          <Card>
            <CardHeader icon={<FlaskConical />} title={t("teachers.lab.title")} />
            <p className="text-[0.82rem] leading-relaxed text-ink-3">{t("teachers.lab.body")}</p>
            <LabHomeLink />
          </Card>
        </div>
      </div>
    </>
  );
}

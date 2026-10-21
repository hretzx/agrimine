"use client";

import { BarChart3, GitFork, Link2, Sun, Users } from "lucide-react";
import { FarmsChart, NeedsChart } from "@/components/farm/charts";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader } from "@/components/ui/card";
import { ErrorState, Loading } from "@/components/ui/states";
import { Track } from "@/components/ui/track";
import { useAccuracy, useFarms, useGain, useMeta, useNeeds, usePatterns } from "@/lib/data";
import { familyColor, clusterColor } from "@/lib/charts";
import { useI18n } from "@/lib/i18n/provider";
import { axisTitle, cropName, familyName, featureLabel } from "@/lib/labels";
import type { CheckOut } from "./types";
import { patternItem } from "./format";

const MARK = "#ff5a4f";
const Legend = ({ color, children, square }: { color: string; children: React.ReactNode; square?: boolean }) => (
  <span className="inline-flex items-center gap-1.5"><i className={`size-2 ${square ? "rounded-[2px]" : "rounded-full"}`} style={{ background: color }} />{children}</span>
);

/** K-Means groups of similar conditions, drawn on rainfall and temperature; your own check is the red X. */
export function FarmsCard({ check }: { check?: CheckOut }) {
  const { t, locale } = useI18n();
  const meta = useMeta().data;
  const farms = useFarms(4, check?.id);
  const data = farms.data;
  return (
    <Card>
      <CardHeader icon={<Users />} title={t("farms.title")} subtitle={t("farms.sub")} />
      {farms.error ? <ErrorState onRetry={() => farms.mutate()} /> : !data ? <Loading className="h-60" /> : (
        <div data-testid="farms">
          <FarmsChart data={data} yours={check?.values} xTitle={axisTitle(meta?.features, "rainfall", locale)} yTitle={axisTitle(meta?.features, "temperature", locale)} yourLabel={t("farms.yourField")} />
          <div className="mt-2 flex flex-wrap gap-x-3.5 gap-y-1 text-[0.72rem] text-ink-3">
            {data.clusters.map((c) => (
              <Legend key={c.cluster} color={clusterColor(c.cluster)}>
                {t("farms.group", { n: c.cluster + 1, count: c.records.toLocaleString("en") })} · {t("farms.mostOften", { crop: cropName(c.top_crop, locale), share: `${Math.round(c.share * 100)}%` })}
              </Legend>
            ))}
            {check && <Legend color={MARK} square>{t("farms.yourField")}</Legend>}
          </div>
        </div>
      )}
    </Card>
  );
}

/** What each crop needs: average temperature and rainfall (bubble size = humidity), coloured by crop family. */
export function NeedsCard({ check }: { check?: CheckOut }) {
  const { t, locale } = useI18n();
  const meta = useMeta().data;
  const needs = useNeeds();
  const families = Array.from(new Set(needs.data?.map((n) => n.crop.family) ?? []));
  return (
    <Card>
      <CardHeader icon={<Sun />} title={t("needs.title")} subtitle={t("needs.sub")} />
      {needs.error ? <ErrorState onRetry={() => needs.mutate()} /> : !needs.data ? <Loading className="h-60" /> : (
        <div data-testid="needs">
          <NeedsChart data={needs.data} yours={check?.values} xTitle={axisTitle(meta?.features, "temperature", locale)} yTitle={axisTitle(meta?.features, "rainfall", locale)} yourLabel={t("farms.yourField")} />
          <div className="mt-2 flex flex-wrap gap-x-3.5 gap-y-1 text-[0.72rem] text-ink-3">
            {families.map((f) => <Legend key={f} color={familyColor(f)}>{familyName(meta?.families, f, locale)}</Legend>)}
            {check && <Legend color={MARK} square>{t("farms.yourField")}</Legend>}
          </div>
        </div>
      )}
    </Card>
  );
}

/** ID3 information gain of every reading at the root of the tree, as hatch bars. */
export function GainCard() {
  const { t, locale } = useI18n();
  const meta = useMeta().data;
  const gain = useGain();
  const top = gain.data?.[0]?.gain ?? 1;
  return (
    <Card>
      <CardHeader icon={<GitFork />} title={t("gain.title")} subtitle={t("gain.sub")} action={<Badge tone="lavender">{t("badge.technical")}</Badge>} />
      {gain.error ? <ErrorState onRetry={() => gain.mutate()} /> : !gain.data ? <Loading className="h-52" /> : (
        <div className="space-y-2.5" data-testid="gain">
          {gain.data.map((g) => (
            <div key={g.feature} className="grid grid-cols-[6rem_1fr_2.4rem] items-center gap-2.5 text-[0.8rem]">
              <span className="truncate text-ink-2">{featureLabel(meta?.features, g.feature, locale).replace(/\s*\(.*\)$/, "")}</span>
              <Track hatch value={(g.gain / top) * 100} label={`${g.feature}: ${g.gain.toFixed(2)}`} color="linear-gradient(90deg,#e9c23f,#f4cf58)" className="[&>div]:h-2.5" />
              <b className="text-right tabular-nums">{g.gain.toFixed(2)}</b>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

/** The strongest Apriori rules that end in a crop, with their support, confidence and lift. */
export function PatternsCard() {
  const { t, locale } = useI18n();
  const meta = useMeta().data;
  const patterns = usePatterns(3);
  const word = (w: string) => t(`item.${w}` as never);
  return (
    <Card>
      <CardHeader icon={<Link2 />} title={t("patterns.title")} subtitle={patterns.data ? t("patterns.sub", { n: patterns.data.total.toLocaleString("en") }) : undefined} action={<Badge tone="lavender">{t("badge.technical")}</Badge>} />
      {patterns.error ? <ErrorState onRetry={() => patterns.mutate()} /> : !patterns.data ? <Loading className="h-52" /> : (
        <div className="space-y-2" data-testid="patterns">
          {patterns.data.items.map((p, i) => (
            <div key={i} className="rounded-tile bg-inset p-3 shadow-[inset_0_0_0_1px_var(--line-2)]">
              <p className="text-[0.82rem] font-semibold leading-snug">{p.antecedent.map((a) => patternItem(a, meta, locale, word)).join(" + ")} → {patternItem(p.consequent, meta, locale, word)}</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                <Badge tone="mint">{t("patterns.confidence", { v: `${Math.round(p.confidence * 100)}%` })}</Badge>
                <Badge tone="lavender">{t("patterns.lift", { v: p.lift.toFixed(1) })}</Badge>
                <Badge tone="sky">{t("patterns.support", { v: `${(p.support * 100).toFixed(1)}%` })}</Badge>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

/** Held-out accuracy of the two classifiers, with the split and the metric stated. */
export function AccuracyCard() {
  const { t } = useI18n();
  const acc = useAccuracy();
  return (
    <Card>
      <CardHeader icon={<BarChart3 />} title={t("accuracy.title")} subtitle={acc.data ? t("accuracy.sub", { n: acc.data.test_rows }) : undefined} action={<Badge tone="lavender">{t("badge.technical")}</Badge>} />
      {acc.error ? <ErrorState onRetry={() => acc.mutate()} /> : !acc.data ? <Loading className="h-52" /> : (
        <div className="space-y-5" data-testid="accuracy">
          {acc.data.models.map((m, i) => (
            <div key={m.model}>
              <div className="mb-1.5 flex justify-between text-[0.82rem]"><b>{m.model}</b><b className="tabular-nums">{(m.accuracy * 100).toFixed(1)}%</b></div>
              <Track hatch value={m.accuracy * 100} label={`${m.model}: ${(m.accuracy * 100).toFixed(1)}%`} color={i === 0 ? "linear-gradient(90deg,#b79ced,#9d7de0)" : "linear-gradient(90deg,#f4cf58,#e9b22e)"} className="[&>div]:h-3" />
            </div>
          ))}
          <p className="text-xs leading-relaxed text-ink-3">
            {t("accuracy.note", { train: Math.round((acc.data.train_rows / (acc.data.train_rows + acc.data.test_rows)) * 100), test: Math.round((acc.data.test_rows / (acc.data.train_rows + acc.data.test_rows)) * 100), seed: acc.data.seed })}
          </p>
        </div>
      )}
    </Card>
  );
}


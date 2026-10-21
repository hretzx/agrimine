"use client";

import { GitBranch, Split, Waypoints } from "lucide-react";
import { useId } from "react";
import { CropGlyph } from "@/components/farm/crop-glyph";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader } from "@/components/ui/card";
import { Segmented } from "@/components/ui/segmented";
import type { CropRef, HierarchicalReport } from "@/lib/api/client";
import { clusterColor, linear, niceTicks } from "@/lib/charts";
import { useI18n } from "@/lib/i18n/provider";
import { cropName } from "@/lib/labels";

export const METHODS = ["ward", "average", "complete", "single"] as const;

/** The linkage choice and the cut (k), with the two numbers that describe the tree. */
export function HierControls({ method, setMethod, k, setK, report }: { method: string; setMethod: (m: string) => void; k: number; setK: (k: number) => void; report?: HierarchicalReport }) {
  const { t } = useI18n();
  const id = useId();
  return (
    <Card data-testid="hier-controls">
      <div className="grid grid-cols-1 items-start gap-5 md:grid-cols-[1.3fr_1fr]">
        <div>
          <p className="mb-1.5 text-xs font-semibold text-ink-2">{t("hier.linkage")}</p>
          <Segmented<string> label={t("hier.linkage")} value={method} onChange={setMethod} options={METHODS.map((m) => ({ value: m, label: t(`hier.m.${m}`) }))} className="flex-wrap" />
          <p className="mt-1.5 text-[0.7rem] leading-snug text-ink-3" data-testid="hier-method-help">{t(`hier.m.${method as (typeof METHODS)[number]}.help`)}</p>
        </div>
        <div>
          <label htmlFor={id} className="flex items-baseline justify-between text-xs font-semibold text-ink-2"><span>{t("hier.k")}</span><b className="text-base tabular-nums" data-testid="hier-k">{k}</b></label>
          <input id={id} type="range" min={2} max={10} step={1} value={k} onChange={(e) => setK(Number(e.target.value))} aria-valuetext={t("km.k.text", { k })} data-testid="hier-slider" className="mt-2 h-8 w-full cursor-pointer accent-[var(--brand)]" />
        </div>
      </div>
      {report && (
        <dl className="mt-4 grid grid-cols-3 gap-3 text-xs">
          {([["hier.crops", String(report.crops.length), "hier-crops"], ["hier.coph", report.cophenetic.toFixed(3), "hier-coph"], ["hier.last", report.last_height.toFixed(2), "hier-last"]] as const).map(([label, v, tid]) => (
            <div key={tid} className="rounded-tile bg-inset p-3"><dt className="text-ink-3">{t(label)}</dt><dd className="mt-1 text-lg font-semibold tabular-nums" data-testid={tid}>{v}</dd></div>
          ))}
        </dl>
      )}
    </Card>
  );
}

/** The family tree: crops along the bottom, merges as upside-down U shapes, coloured by the clusters from the cut (dashed line). */
export function Dendrogram({ report }: { report: HierarchicalReport }) {
  const { t, locale } = useI18n();
  const W = 640, H = 330, left = 40, right = 8, top = 10, bottom = 100;
  const sx = linear([0, 220], [left, W - right]);
  const ymax = Math.max(report.last_height, report.threshold ?? 0) * 1.05;
  const sy = linear([0, ymax], [H - bottom, top]);
  const ticks = niceTicks(0, report.last_height, 5);
  const byIndex = report.order.map((i) => report.crops[i]);
  return (
    <Card data-testid="hier-tree">
      <CardHeader icon={<GitBranch />} title={t("hier.tree.title")} subtitle={t("hier.tree.sub")} />
      <div tabIndex={0} role="region" aria-label={t("hier.tree.title")} className="-mx-5 overflow-x-auto px-5 outline-none focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-brand">
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t("hier.tree.title")} className="h-auto w-full min-w-[34rem]">
          <g className="fill-ink-3 text-[9px]">
            {ticks.map((v) => (
              <g key={v}><line x1={left} x2={W - right} y1={sy(v)} y2={sy(v)} stroke="var(--line)" strokeDasharray="1 5" /><text x={left - 6} y={sy(v) + 3} textAnchor="end">{v}</text></g>
            ))}
            <text transform={`translate(8 ${(H - bottom) / 2}) rotate(-90)`} textAnchor="middle">{t("hier.height", { m: t(`hier.m.${report.method}`) })}</text>
          </g>
          {report.segments.map((s, i) => (
            <polyline key={i} data-testid="hier-segment" fill="none" strokeWidth={2} strokeLinejoin="round" stroke={s.cluster === null ? "var(--ink-3)" : clusterColor(s.cluster)}
                      points={s.x.map((x, j) => `${sx(x)},${sy(s.y[j])}`).join(" ")}><title>{t("hier.merge", { h: s.height.toFixed(2) })}</title></polyline>
          ))}
          {report.threshold !== null && <line x1={left} x2={W - right} y1={sy(report.threshold)} y2={sy(report.threshold)} stroke="var(--ink)" strokeWidth={1} strokeDasharray="5 4" />}
          {byIndex.map((c, p) => <text key={c.key} data-testid="hier-leaf" transform={`translate(${sx(10 * p + 5)} ${H - bottom + 10}) rotate(-60)`} textAnchor="end" className="fill-ink text-[9px] font-medium">{cropName(c, locale)}</text>)}
        </svg>
      </div>
    </Card>
  );
}

function Members({ crops }: { crops: CropRef[] }) {
  const { locale } = useI18n();
  return (
    <ul className="flex flex-wrap gap-1.5">
      {crops.map((c) => <li key={c.key} className="inline-flex items-center gap-1.5 rounded-full bg-inset py-1 pl-1 pr-2.5 text-xs font-semibold shadow-[inset_0_0_0_1px_var(--line)]"><CropGlyph crop={c.key} size={20} />{cropName(c, locale)}</li>)}
    </ul>
  );
}

/** The k clusters from the cut. */
export function HierClusters({ report }: { report: HierarchicalReport }) {
  const { t } = useI18n();
  return (
    <Card data-testid="hier-clusters">
      <CardHeader icon={<Waypoints />} title={t("hier.clusters.title", { k: report.k })} subtitle={t("hier.clusters.sub")} />
      <ol className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {report.clusters.map((members, c) => (
          <li key={c} data-testid="hier-cluster" className="rounded-tile bg-inset p-3.5 shadow-[inset_0_0_0_1px_var(--line-2)]">
            <p className="mb-2 flex items-center gap-2 text-xs font-bold"><i className="size-2.5 rounded-full" style={{ background: clusterColor(c) }} />{t("hier.cluster", { n: c + 1, count: members.length })}</p>
            <Members crops={members} />
          </li>
        ))}
      </ol>
    </Card>
  );
}

/** DIANA: splitting from the top, and whether it agrees with the bottom-up clusters. */
export function Diana({ report }: { report: HierarchicalReport }) {
  const { t, locale } = useI18n();
  const names = (cs: CropRef[]) => cs.map((c) => cropName(c, locale)).join(", ");
  return (
    <Card data-testid="hier-diana">
      <CardHeader icon={<Split />} title={t("hier.diana.title")} subtitle={t("hier.diana.sub")} />
      <div tabIndex={0} role="region" aria-label={t("hier.diana.title")} className="-mx-5 overflow-x-auto px-5 outline-none focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-brand">
        <table className="w-full min-w-[40rem] border-separate border-spacing-0 text-[0.82rem]">
          <thead><tr className="text-left text-xs text-ink-3">{[t("hier.diana.step"), t("hier.diana.diameter"), t("hier.diana.splits"), t("hier.diana.splinter"), t("hier.diana.rest")].map((label) => <th key={label} scope="col" className="px-2 py-2 font-semibold">{label}</th>)}</tr></thead>
          <tbody>
            {report.diana_steps.map((s) => (
              <tr key={s.step} data-testid="hier-diana-row">
                <td className="border-b border-line-2 px-2 py-2 tabular-nums">{s.step}</td>
                <td className="border-b border-line-2 px-2 py-2 tabular-nums">{s.diameter.toFixed(2)}</td>
                <td className="whitespace-nowrap border-b border-line-2 px-2 py-2">{t("hier.diana.crops", { n: s.size })}</td>
                <td className="border-b border-line-2 px-2 py-2 font-semibold">{names(s.splinter)}</td>
                <td className="border-b border-line-2 px-2 py-2 text-ink-3">{names(s.rest)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-4"><Badge tone={report.same ? "mint" : "sky"} data-testid="hier-same">{t(report.same ? "hier.same" : "hier.differ", { k: report.k, m: t(`hier.m.${report.method}`) })}</Badge></div>
      {!report.same && (
        <div className="mt-3 space-y-2" data-testid="hier-diana-clusters">
          <p className="text-xs text-ink-3">{t("hier.differ.note")}</p>
          {report.diana_clusters.map((members, c) => <div key={c}><p className="mb-1 text-xs font-bold">{t("hier.diana.cluster", { n: c + 1 })}</p><Members crops={members} /></div>)}
        </div>
      )}
    </Card>
  );
}

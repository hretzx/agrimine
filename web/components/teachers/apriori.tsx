"use client";

import { ArrowDown, ArrowUp, Link2, ListOrdered, Table2 } from "lucide-react";
import { useId, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader } from "@/components/ui/card";
import { Segmented } from "@/components/ui/segmented";
import { Select } from "@/components/ui/select";
import { Track } from "@/components/ui/track";
import type { AprioriQuery, AprioriReport, Meta } from "@/lib/api/client";
import { useI18n } from "@/lib/i18n/provider";
import { cropName } from "@/lib/labels";
import { patternItem } from "@/components/home/format";

type Rule = AprioriReport["rules"][number];

/** "N=low" items turned into words in the current language. */
export function useRuleText(meta?: Meta) {
  const { t, locale } = useI18n();
  const word = (w: string) => t(`item.${w}` as never);
  return {
    rule: (r: Rule) => `${r.antecedent.map((a) => patternItem(a, meta, locale, word)).join(" + ")} → ${patternItem(r.consequent, meta, locale, word)}`,
    ifPart: (r: Rule) => r.antecedent.map((a) => patternItem(a, meta, locale, word)).join(" + "),
    thenPart: (r: Rule) => patternItem(r.consequent, meta, locale, word),
  };
}

/** The settings: minimum support, minimum confidence, pattern size, crop filter, crop-only switch. */
export function AprioriControls({ q, set, meta }: { q: AprioriQuery; set: (next: AprioriQuery) => void; meta?: Meta }) {
  const { t, locale } = useI18n();
  const sid = useId(), cid = useId();
  const crops = [{ value: "all", label: t("apr.allCrops") }, ...(meta?.crops ?? []).map((c) => ({ value: c.key, label: cropName(c, locale) }))];
  return (
    <Card data-testid="apr-controls">
      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
        <div>
          <label htmlFor={sid} className="flex items-baseline justify-between text-xs font-semibold text-ink-2"><span>{t("apr.support")}</span><b className="text-base tabular-nums" data-testid="apr-support-v">{q.minSupport.toFixed(3)}</b></label>
          <input id={sid} type="range" min={0.005} max={0.1} step={0.005} value={q.minSupport} onChange={(e) => set({ ...q, minSupport: Number(Number(e.target.value).toFixed(3)) })} data-testid="apr-support" className="mt-2 h-8 w-full cursor-pointer accent-[var(--brand)]" />
          <p className="text-[0.7rem] leading-snug text-ink-3">{t("apr.support.help")}</p>
        </div>
        <div>
          <label htmlFor={cid} className="flex items-baseline justify-between text-xs font-semibold text-ink-2"><span>{t("apr.conf")}</span><b className="text-base tabular-nums" data-testid="apr-conf-v">{q.minConfidence.toFixed(2)}</b></label>
          <input id={cid} type="range" min={0.5} max={1} step={0.05} value={q.minConfidence} onChange={(e) => set({ ...q, minConfidence: Number(Number(e.target.value).toFixed(2)) })} data-testid="apr-conf" className="mt-2 h-8 w-full cursor-pointer accent-[var(--brand)]" />
          <p className="text-[0.7rem] leading-snug text-ink-3">{t("apr.conf.help")}</p>
        </div>
        <div>
          <p className="mb-1.5 text-xs font-semibold text-ink-2">{t("apr.size")}</p>
          <Segmented<string> label={t("apr.size")} value={String(q.maxLen)} onChange={(v) => set({ ...q, maxLen: Number(v) })} options={[2, 3, 4, 5].map((n) => ({ value: String(n), label: String(n) }))} />
          <p className="mt-1.5 text-[0.7rem] leading-snug text-ink-3">{t("apr.size.help")}</p>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap items-end gap-x-6 gap-y-3 border-t border-line pt-4">
        <Select label={t("apr.crop")} value={q.crop || "all"} onChange={(v) => set({ ...q, crop: v === "all" ? "" : v })} options={crops} className="min-w-[14rem]" />
        <label className="flex min-h-10 cursor-pointer items-center gap-2.5 text-sm font-medium">
          <input type="checkbox" checked={q.onlyCrop} onChange={(e) => set({ ...q, onlyCrop: e.target.checked })} data-testid="apr-onlycrop" className="size-4 accent-[var(--brand)]" />
          {t("apr.onlyCrop")}
        </label>
      </div>
    </Card>
  );
}

/** Three numbers: itemsets, rules, and the measured mining time. */
export function AprioriStats({ report }: { report: AprioriReport }) {
  const { t } = useI18n();
  const items = [["apr.itemsets", report.itemsets.toLocaleString("en"), "apr-itemsets"], ["apr.rules", report.rules_total.toLocaleString("en"), "apr-rules"], ["apr.time", `${report.seconds.toFixed(2)} s`, "apr-time"]] as const;
  return (
    <dl className="grid grid-cols-3 gap-3" data-testid="apr-stats">
      {items.map(([k, v, id]) => <div key={id} className="rounded-tile bg-card p-3.5 shadow-card"><dt className="text-xs text-ink-3">{t(k)}</dt><dd className="mt-1 text-xl font-semibold tabular-nums" data-testid={id}>{v}</dd></div>)}
    </dl>
  );
}

/** The three strongest rules. */
export function AprioriTop({ report, meta }: { report: AprioriReport; meta?: Meta }) {
  const { t } = useI18n();
  const text = useRuleText(meta);
  return (
    <Card data-testid="apr-top">
      <CardHeader icon={<Link2 />} title={t("apr.top.title")} subtitle={t("apr.top.sub")} />
      <ol className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        {report.rules.slice(0, 3).map((r, i) => (
          <li key={i} data-testid="apr-top-rule" className="rounded-tile bg-inset p-3.5 shadow-[inset_0_0_0_1px_var(--line-2)]">
            <p className="text-xs font-bold text-ink-3">#{i + 1}</p>
            <p className="mt-1 text-[0.85rem] font-semibold leading-snug">{text.rule(r)}</p>
            <div className="mt-2.5 flex flex-wrap gap-1.5">
              <Badge tone="mint">{t("patterns.confidence", { v: `${Math.round(r.confidence * 100)}%` })}</Badge>
              <Badge tone="lavender">{t("patterns.lift", { v: r.lift.toFixed(1) })}</Badge>
              <Badge tone="sky">{t("patterns.support", { v: `${(r.support * 100).toFixed(1)}%` })}</Badge>
            </div>
          </li>
        ))}
      </ol>
    </Card>
  );
}

type SortKey = "lift" | "confidence" | "support";

/** Every rule (the strongest hundred), sortable by clicking a column heading. */
export function AprioriTable({ report, meta }: { report: AprioriReport; meta?: Meta }) {
  const { t } = useI18n();
  const text = useRuleText(meta);
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 } | null>(null);
  const rows = useMemo(() => (sort ? [...report.rules].sort((a, b) => (a[sort.key] - b[sort.key]) * sort.dir) : report.rules), [report, sort]);
  const head = (key: SortKey, label: string) => (
    <th scope="col" aria-sort={sort?.key === key ? (sort.dir === 1 ? "ascending" : "descending") : "none"} className="px-2 py-1 font-semibold">
      <button type="button" onClick={() => setSort(sort?.key === key && sort.dir === -1 ? { key, dir: 1 } : { key, dir: -1 })} data-testid={`apr-sort-${key}`}
              className="inline-flex min-h-10 min-w-10 items-center justify-center gap-1 rounded-md px-1 outline-none hover:text-ink focus-visible:outline-2 focus-visible:outline-brand">
        {label}{sort?.key === key && (sort.dir === 1 ? <ArrowUp className="size-3" aria-hidden="true" /> : <ArrowDown className="size-3" aria-hidden="true" />)}
      </button>
    </th>
  );
  return (
    <Card data-testid="apr-table">
      <CardHeader icon={<Table2 />} title={t("apr.all.title")} subtitle={t("apr.all.sub")} />
      <div tabIndex={0} role="region" aria-label={t("apr.all.title")} className="-mx-5 max-h-[32rem] overflow-auto px-5 outline-none focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-brand">
        <table className="w-full min-w-[40rem] border-separate border-spacing-0 text-[0.82rem]">
          <thead className="sticky top-0 bg-card text-left text-xs text-ink-3">
            <tr><th scope="col" className="px-2 py-2 font-semibold">{t("apr.if")}</th><th scope="col" className="px-2 py-2 font-semibold">{t("apr.then")}</th>{head("support", t("apr.col.support"))}{head("confidence", t("apr.col.conf"))}{head("lift", t("apr.col.lift"))}</tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} data-testid="apr-row">
                <td className="border-b border-line-2 px-2 py-2">{text.ifPart(r)}</td>
                <td className="whitespace-nowrap border-b border-line-2 px-2 py-2 font-semibold">{text.thenPart(r)}</td>
                <td className="border-b border-line-2 px-2 py-2 tabular-nums">{r.support.toFixed(4)}</td>
                <td className="border-b border-line-2 px-2 py-2 tabular-nums">{Math.round(r.confidence * 100)}%</td>
                <td className="border-b border-line-2 px-2 py-2 font-bold tabular-nums">{r.lift.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-ink-3" data-testid="apr-shown">{t("apr.shown", { n: report.rules.length.toLocaleString("en"), total: report.rules_total.toLocaleString("en") })}</p>
    </Card>
  );
}

/** The ten strongest rules by lift as bars; lift 1 = no link. */
export function AprioriLift({ report, meta }: { report: AprioriReport; meta?: Meta }) {
  const { t } = useI18n();
  const text = useRuleText(meta);
  const top = report.rules.slice(0, 10), max = Math.max(...top.map((r) => r.lift), 1);
  return (
    <Card data-testid="apr-lift">
      <CardHeader icon={<ListOrdered />} title={t("apr.lift.title")} subtitle={t("apr.lift.sub")} />
      <ol className="space-y-2.5">
        {top.map((r, i) => (
          <li key={i} className="grid grid-cols-1 gap-1 text-xs sm:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_3rem] sm:items-center sm:gap-3">
            <span className="font-medium leading-snug">{text.rule(r)}</span>
            <Track hatch value={(r.lift / max) * 100} label={`${text.rule(r)}: ${r.lift.toFixed(2)}`} color={i === 0 ? "linear-gradient(90deg,#ff8a7f,#ff5a4f)" : "linear-gradient(90deg,#b79ced,#9d7de0)"} className="[&>div]:h-2.5" />
            <b className="tabular-nums sm:text-right">{r.lift.toFixed(2)}</b>
          </li>
        ))}
      </ol>
    </Card>
  );
}

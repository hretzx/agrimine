"use client";

import { Brain, Calculator, GitFork, ListOrdered, Scale } from "lucide-react";
import { CropGlyph } from "@/components/farm/crop-glyph";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader } from "@/components/ui/card";
import { Track } from "@/components/ui/track";
import type { CropRef, FeatureInfo, NBReport } from "@/lib/api/client";
import { useI18n } from "@/lib/i18n/provider";
import { cropName, featureLabel } from "@/lib/labels";
import { pct } from "@/components/home/format";
import { num } from "./id3";

const PURPLE = "linear-gradient(90deg,#b49bf0,#9b7de6)";
const YELLOW = "linear-gradient(90deg,#f4cf58,#e9b22e)";

/** "temperature" -> its label; "prior" -> "How common the crop is". */
function useName(features?: FeatureInfo[]) {
  const { t, locale } = useI18n();
  return (key: string) => (key === "prior" ? t("nb.prior") : featureLabel(features, key, locale).replace(/\s*\(.*\)$/, ""));
}

/** Both classifiers' answers side by side, and whether they agree. */
export function NbVerdict({ report }: { report: NBReport }) {
  const { t, locale } = useI18n();
  const { id3, nb, agree } = report;
  const card = (testId: string, icon: React.ReactNode, title: string, crop: CropRef, rows: [string, string, string][]) => (
    <Card data-testid={testId} className={agree ? "shadow-[var(--shadow-card),inset_0_0_0_1.5px_var(--mint)]" : ""}>
      <CardHeader icon={icon} title={title} />
      <div className="flex items-center gap-3.5">
        <CropGlyph crop={crop.key} size={56} />
        <p className="text-[2rem] font-light leading-none tracking-[-0.04em]" data-testid={`${testId}-crop`}>{cropName(crop, locale)}</p>
      </div>
      <dl className="mt-4 space-y-1.5 text-xs">
        {rows.map(([k, v, id]) => (<div key={k} className="flex justify-between gap-3"><dt className="text-ink-3">{k}</dt><dd className="font-bold tabular-nums" data-testid={id}>{v}</dd></div>))}
      </dl>
    </Card>
  );
  return (
    <div className="space-y-3">
      <Badge tone={agree ? "mint" : "butter"} data-testid="nb-agree">{agree ? t("nb.agree") : t("nb.disagree")}</Badge>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {card("nb-id3", <GitFork />, t("nb.id3"), id3.crop, [[t("nb.purity"), pct(id3.purity), "nb-purity"], [t("id3.acc.title"), pct(id3.accuracy), "nb-id3-acc"]])}
        {card("nb-nb", <Brain />, t("nb.nb"), nb.crop, [[t("nb.posterior"), pct(nb.probability), "nb-prob"], [t("id3.acc.title"), pct(nb.accuracy), "nb-nb-acc"]])}
      </div>
      {!agree && <p className="text-xs text-ink-3" data-testid="nb-disagree-note">{t("nb.disagree.note", { crop: cropName(id3.crop, locale), p: pct(id3.nb_probability) })}</p>}
    </div>
  );
}

/** Naive Bayes spreads probability over crops: the six most likely. */
export function NbTop({ report }: { report: NBReport }) {
  const { t, locale } = useI18n();
  return (
    <Card data-testid="nb-top">
      <CardHeader icon={<ListOrdered />} title={t("nb.top.title")} subtitle={t("nb.top.sub")} />
      <ol className="space-y-2.5">
        {report.top.map((c, i) => (
          <li key={c.crop.key} className="grid grid-cols-[2.2rem_minmax(0,1fr)_3.6rem] items-center gap-3">
            <CropGlyph crop={c.crop.key} size={34} />
            <div className="min-w-0"><p className="truncate text-sm font-semibold">{cropName(c.crop, locale)}</p>
              <Track hatch value={c.probability * 100} label={`${cropName(c.crop, locale)}: ${pct(c.probability)}`} color={i === 0 ? PURPLE : "linear-gradient(90deg,#d5c8f6,#c0aef0)"} className="mt-1 [&>div]:h-2" /></div>
            <b className="text-right text-sm tabular-nums">{pct(c.probability)}</b>
          </li>
        ))}
      </ol>
    </Card>
  );
}

/** Which readings pushed the decision: signed bars, right = the winner, left = the runner-up. */
export function NbWhy({ report, features }: { report: NBReport; features?: FeatureInfo[] }) {
  const { t, locale } = useI18n();
  const name = useName(features);
  const winner = cropName(report.nb.crop, locale), runner = cropName(report.runner_up, locale);
  const max = Math.max(...report.why.map((w) => Math.abs(w.difference)), 1e-9);
  const times = Math.exp(Math.min(report.why_total, 50));
  return (
    <Card data-testid="nb-why">
      <CardHeader icon={<Scale />} title={t("nb.why.title")} subtitle={t("nb.why.sub", { winner, runner })} />
      <ul className="space-y-2">
        {report.why.map((w) => {
          const win = w.difference >= 0, width = (Math.abs(w.difference) / max) * 50;
          return (
            <li key={w.feature} data-testid="nb-why-row" className="grid grid-cols-[6.5rem_minmax(0,1fr)_3.6rem] items-center gap-2.5 text-xs sm:grid-cols-[8rem_minmax(0,1fr)_3.6rem]">
              <span className="truncate text-ink-2">{name(w.feature)}</span>
              <span role="img" aria-label={`${name(w.feature)}: ${win ? winner : runner} ${w.difference > 0 ? "+" : ""}${w.difference.toFixed(2)}`} className="relative h-3 rounded-full bg-track">
                <i className="absolute inset-y-0 left-1/2 w-px bg-ink-3/60" />
                <i className="absolute inset-y-0 rounded-full" style={{ width: `${width}%`, [win ? "left" : "right"]: "50%", background: win ? "var(--lavender)" : "var(--sky)" }} />
              </span>
              <b className="text-right tabular-nums">{w.difference > 0 ? "+" : ""}{w.difference.toFixed(2)}</b>
            </li>
          );
        })}
      </ul>
      <div className="mt-2 flex justify-between text-[0.68rem] text-ink-3"><span>← {runner}</span><span>{winner} →</span></div>
      <p className="mt-3 text-xs leading-relaxed text-ink-3" data-testid="nb-why-total">{t("nb.why.total", { total: `${report.why_total > 0 ? "+" : ""}${report.why_total.toFixed(2)}`, winner, runner, times: times.toPrecision(3) })}</p>
    </Card>
  );
}

/** Bayes' formula with the reader's own numbers, step by step. */
export function NbWorked({ report, features }: { report: NBReport; features?: FeatureInfo[] }) {
  const { t, locale } = useI18n();
  const name = useName(features);
  const w = report.worked, crop = cropName(w.crop, locale);
  return (
    <Card data-testid="nb-worked">
      <CardHeader icon={<Calculator />} title={t("nb.worked.title")} subtitle={t("nb.worked.sub", { crop })} />
      <p className="mb-3 overflow-x-auto rounded-tile bg-inset px-3.5 py-2.5 font-mono text-[0.78rem] leading-relaxed">P(crop | x) ∝ P(crop) · ∏<sub>f=1..7</sub> 1/√(2πσ<sub>f</sub>²) · e<sup>−(x<sub>f</sub>−μ<sub>f</sub>)² / 2σ<sub>f</sub>²</sup></p>
      <div tabIndex={0} role="region" aria-label={t("nb.worked.title")} className="-mx-5 overflow-x-auto px-5 outline-none focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-brand">
        <table className="w-full min-w-[34rem] border-separate border-spacing-0 whitespace-nowrap text-[0.82rem]">
          <thead><tr className="text-left text-xs text-ink-3">
            <th className="px-2 py-2 font-semibold" /><th className="px-2 py-2 font-semibold">{t("nb.worked.value")}</th>
            <th className="px-2 py-2 font-semibold">{t("nb.worked.mean", { crop })}</th><th className="px-2 py-2 font-semibold">σ</th>
            <th className="px-2 py-2 font-semibold">{t("nb.worked.distance")}</th><th className="px-2 py-2 font-semibold">{t("nb.worked.ll")}</th></tr></thead>
          <tbody>
            {w.features.map((f) => (
              <tr key={f.feature} data-testid="nb-worked-row">
                <th scope="row" className="border-b border-line-2 px-2 py-2 text-left font-semibold">{name(f.feature)}</th>
                <td className="border-b border-line-2 px-2 py-2 tabular-nums">{num(f.value)}</td>
                <td className="border-b border-line-2 px-2 py-2 tabular-nums">{num(f.mean)}</td>
                <td className="border-b border-line-2 px-2 py-2 tabular-nums">{num(f.sigma)}</td>
                <td className="border-b border-line-2 px-2 py-2 tabular-nums">{num(f.distance)}</td>
                <td className="border-b border-line-2 px-2 py-2 font-bold tabular-nums">{num(f.log_likelihood)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul className="mt-3 list-disc space-y-1 pl-5 text-[0.82rem] leading-relaxed text-ink-2" data-testid="nb-worked-steps">
        <li>{t("nb.worked.s1", { crop, lp: num(w.log_prior), p: pct(w.prior) })}</li>
        <li>{t("nb.worked.s2", { s: num(w.sum_log_likelihood) })}</li>
        <li>{t("nb.worked.s3", { lp: num(w.log_prior), s: num(w.sum_log_likelihood), j: num(w.joint) })}</li>
        <li>{t("nb.worked.s4", { n: w.n_crops, crop, p: pct(report.nb.probability) })}</li>
      </ul>
    </Card>
  );
}

/** Held-out accuracy of both models for every crop. */
export function NbPerCrop({ report }: { report: NBReport }) {
  const { t, locale } = useI18n();
  const perfect = (k: "id3" | "nb") => report.per_crop.filter((p) => p[k] === 1).length;
  return (
    <Card data-testid="nb-percrop">
      <CardHeader title={t("nb.per.title")} subtitle={t("nb.per.sub")} action={<span className="flex gap-3 text-[0.7rem] font-semibold text-ink-3"><span><i className="mr-1 inline-block size-2 rounded-full bg-butter" />ID3</span><span><i className="mr-1 inline-block size-2 rounded-full bg-lavender" />Naive Bayes</span></span>} />
      <ul className="space-y-2">
        {report.per_crop.map((p) => (
          <li key={p.crop.key} data-testid="nb-percrop-row" className="grid grid-cols-[6.5rem_minmax(0,1fr)] items-center gap-3 text-xs sm:grid-cols-[8rem_minmax(0,1fr)]">
            <span className="truncate font-semibold">{cropName(p.crop, locale)}</span>
            <span className="space-y-1">
              <span className="flex items-center gap-2"><Track hatch value={p.id3 * 100} label={`${cropName(p.crop, locale)} ID3: ${pct(p.id3)}`} color={YELLOW} className="[&>div]:h-1.5" /><b className="w-14 text-right tabular-nums">{pct(p.id3)}</b></span>
              <span className="flex items-center gap-2"><Track hatch value={p.nb * 100} label={`${cropName(p.crop, locale)} Naive Bayes: ${pct(p.nb)}`} color={PURPLE} className="[&>div]:h-1.5" /><b className="w-14 text-right tabular-nums">{pct(p.nb)}</b></span>
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-ink-3">{t("nb.per.note", { id3: perfect("id3"), nb: perfect("nb"), n: report.per_crop.length })}</p>
    </Card>
  );
}

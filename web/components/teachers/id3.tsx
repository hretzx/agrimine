"use client";

import { Check, GitFork, Info, ListTree, Target } from "lucide-react";
import { CropGlyph } from "@/components/farm/crop-glyph";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader } from "@/components/ui/card";
import { Track } from "@/components/ui/track";
import type { FeatureInfo, ID3Report } from "@/lib/api/client";
import type { MessageKey } from "@/lib/i18n/dictionaries";
import { useI18n } from "@/lib/i18n/provider";
import { cropName, featureLabel } from "@/lib/labels";
import { pct } from "@/components/home/format";

/** 70.8900001 -> "70.89", 80.5 -> "80.5", 12 -> "12" (Latin digits in both languages, like every number in the app). */
export const num = (n: number) => String(Number(n.toFixed(2)));

const LEVELS: Record<string, MessageKey> = { "very low": "id3.level.vlow", low: "id3.level.low", medium: "id3.level.medium", high: "id3.level.high", "very high": "id3.level.vhigh" };

/** "lo <= value < hi" in words: "up to 5", "82.95 or more", "70.89 to 82.95". */
export function rangeWords(t: ReturnType<typeof useI18n>["t"], lo: number | null, hi: number | null) {
  if (lo === null && hi !== null) return t("id3.range.below", { hi: num(hi) });
  if (hi === null && lo !== null) return t("id3.range.above", { lo: num(lo) });
  return t("id3.range.between", { lo: num(lo ?? 0), hi: num(hi ?? 0) });
}

/** The answer: ID3's crop, and how pure the final node was. */
export function Id3Answer({ report }: { report: ID3Report }) {
  const { t, locale } = useI18n();
  const crop = cropName(report.crop, locale);
  return (
    <Card data-testid="id3-answer">
      <CardHeader icon={<GitFork />} title={t("id3.recommends")} subtitle={t("id3.cluster", { n: report.cluster + 1 })} />
      <div className="flex items-center gap-4">
        <CropGlyph crop={report.crop.key} size={64} />
        <p className="text-[2.2rem] font-light leading-none tracking-[-0.04em]" data-testid="id3-crop">{crop}</p>
      </div>
      <p className="mt-4 flex items-baseline justify-between gap-3 text-xs text-ink-3">
        <span>{t("id3.purity", { crop })}</span>
        <b className="text-sm text-ink" data-testid="id3-purity">{pct(report.purity)}</b>
      </p>
      <Track hatch value={report.purity * 100} label={`${t("id3.purity", { crop })}: ${pct(report.purity)}`} color="linear-gradient(90deg,#f4cf58,#e9b22e)" className="mt-2 [&>div]:h-2.5" />
    </Card>
  );
}

/** Held-out accuracy and what it was measured on. */
export function Id3Accuracy({ report }: { report: ID3Report }) {
  const { t } = useI18n();
  return (
    <Card data-testid="id3-accuracy">
      <CardHeader icon={<Target />} title={t("id3.acc.title")} subtitle={t("id3.acc.help")} />
      <p className="text-[2.2rem] font-light leading-none tracking-[-0.04em] tabular-nums" data-testid="id3-accuracy-value">{pct(report.accuracy)}</p>
      <p className="mt-3 text-xs leading-relaxed text-ink-3">{t("id3.acc.sub", { train: report.n_train.toLocaleString("en"), test: report.n_test.toLocaleString("en") })}</p>
    </Card>
  );
}

/** Every question the tree asked about these readings, from the first (the most informative) down to the answer. */
export function Id3Path({ report, features }: { report: ID3Report; features?: FeatureInfo[] }) {
  const { t, locale } = useI18n();
  const maxBits = Math.log2(22);                      // the most uncertainty there can be with 22 crops: the bar shows the share removed
  return (
    <Card data-testid="id3-path">
      <CardHeader icon={<ListTree />} title={t("id3.path.title")} subtitle={t("id3.path.sub")} />
      {report.path.length === 0 ? <p className="text-sm text-ink-3">{t("id3.path.none")}</p> : (
        <ol className="space-y-2.5">
          {report.path.map((s, i) => (
            <li key={i} data-testid="id3-step" className="grid grid-cols-[1.75rem_minmax(0,1fr)] gap-3">
              <span className="relative grid size-7 place-items-center rounded-full bg-card text-xs font-semibold shadow-[inset_0_0_0_1.5px_var(--butter-ink)]">{i + 1}</span>
              <div className="rounded-tile bg-inset px-3.5 py-3">
                <p className="flex flex-wrap items-center gap-2 text-sm font-semibold">
                  {featureLabel(features, s.feature, locale)}
                  <Badge tone="butter">{LEVELS[s.level] ? t(LEVELS[s.level]) : s.level}</Badge>
                </p>
                <p className="mt-1 text-xs text-ink-3">
                  {t("id3.path.value", { v: num(s.value), range: rangeWords(t, s.lo, s.hi) })} · {t("id3.path.rows", { n: s.rows_here.toLocaleString("en") })}
                </p>
                <div className="mt-2 flex items-center gap-3">
                  <span className="w-28 shrink-0 text-xs text-ink-3">{t("id3.path.gain")}</span>
                  <Track hatch value={(s.gain / maxBits) * 100} label={`${t("id3.path.gain")}: ${s.gain.toFixed(3)}`} color="linear-gradient(90deg,#f4cf58,#e9b22e)" className="[&>div]:h-2" />
                  <b className="w-12 text-right text-xs tabular-nums">{s.gain.toFixed(3)}</b>
                </div>
              </div>
            </li>
          ))}
          <li className="grid grid-cols-[1.75rem_minmax(0,1fr)] items-center gap-3">
            <span className="grid size-7 place-items-center rounded-full bg-butter text-[#4d3a00] [&>svg]:size-4"><Check /></span>
            <p className="rounded-tile bg-butter/20 px-3.5 py-2.5 text-sm font-semibold" data-testid="id3-end">{t("id3.path.end", { crop: cropName(report.crop, locale) })}</p>
          </li>
        </ol>
      )}
    </Card>
  );
}

/** Three other crops by profile match: a separate score, not part of the tree. */
export function Id3Alternatives({ report }: { report: ID3Report }) {
  const { t, locale } = useI18n();
  return (
    <Card data-testid="id3-alts">
      <CardHeader title={t("id3.alt.title")} subtitle={t("id3.alt.sub")} />
      <ul className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {report.alternatives.map((a) => (
          <li key={a.crop.key} className="rounded-tile bg-inset p-3">
            <div className="flex items-center gap-2.5"><CropGlyph crop={a.crop.key} size={36} /><b className="text-sm">{cropName(a.crop, locale)}</b></div>
            <p className="mt-2.5 flex justify-between text-xs text-ink-3"><span>{t("id3.alt.match")}</span><b className="text-ink tabular-nums">{Math.round(a.match)} / 100</b></p>
            <Track hatch value={a.match} label={`${cropName(a.crop, locale)}: ${Math.round(a.match)}`} color="linear-gradient(90deg,#f4cf58,#e9b22e)" className="mt-1.5 [&>div]:h-2" />
          </li>
        ))}
      </ul>
    </Card>
  );
}

/** What the tree is made of: bins, depth, leaves, where each reading is cut, and which crops it finds hardest. */
export function Id3Model({ report, features }: { report: ID3Report; features?: FeatureInfo[] }) {
  const { t, locale } = useI18n();
  const m = report.model;
  return (
    <Card data-testid="id3-model">
      <CardHeader icon={<Info />} title={t("id3.model.title")} />
      <p className="text-[0.82rem] leading-relaxed text-ink-3">{t("id3.model.body", { bins: m.n_bins, max: m.max_depth, depth: m.depth, leaves: m.leaves })}</p>
      <h3 className="mb-1.5 mt-4 text-xs font-semibold text-ink-2">{t("id3.model.edges")}</h3>
      <dl className="divide-y divide-line text-xs">
        {Object.entries(m.edges).map(([f, edges]) => (
          <div key={f} className="grid grid-cols-[6.5rem_1fr] gap-3 py-1.5 sm:grid-cols-[8rem_1fr]"><dt className="text-ink-3">{featureLabel(features, f, locale)}</dt><dd className="tabular-nums">{edges.map(num).join(" · ")}</dd></div>
        ))}
      </dl>
      <h3 className="mb-1.5 mt-4 text-xs font-semibold text-ink-2">{t("id3.hard.title")}</h3>
      <ul className="space-y-1.5 text-xs">
        {report.hardest.map((h) => (
          <li key={h.crop.key} className="flex items-center justify-between gap-3"><span className="flex items-center gap-2"><CropGlyph crop={h.crop.key} size={22} />{cropName(h.crop, locale)}</span><b className="tabular-nums">{pct(h.accuracy)}</b></li>
        ))}
      </ul>
    </Card>
  );
}

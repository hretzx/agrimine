"use client";

import { Layers, Map as MapIcon, Table2, TrendingDown } from "lucide-react";
import { useId, useMemo } from "react";
import { Axes, YourField } from "@/components/farm/charts";
import { CropGlyph } from "@/components/farm/crop-glyph";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader } from "@/components/ui/card";
import type { FeatureInfo, KMeansReport } from "@/lib/api/client";
import { clusterColor, linear, niceTicks } from "@/lib/charts";
import { useI18n } from "@/lib/i18n/provider";
import { cropName, featureLabel } from "@/lib/labels";
import { pct } from "@/components/home/format";
import { num } from "./id3";

const group = (n: number) => n + 1;       // the page says "Group 1..k"; the API counts from 0
const nameOf = (features: FeatureInfo[] | undefined, key: string, locale: "en" | "mr") => featureLabel(features, key, locale).replace(/\s*\(.*\)$/, "");

/** The slider for k and the three numbers that say how good this k is. */
export function KControls({ k, setK, report }: { k: number; setK: (k: number) => void; report?: KMeansReport }) {
  const { t } = useI18n();
  const id = useId();
  return (
    <Card data-testid="km-controls">
      <div className="grid grid-cols-1 items-center gap-4 md:grid-cols-[1.2fr_2fr]">
        <div>
          <label htmlFor={id} className="flex items-baseline justify-between text-xs font-semibold text-ink-2"><span>{t("km.k")}</span><b className="text-base tabular-nums" data-testid="km-k">{k}</b></label>
          <input id={id} type="range" min={2} max={10} step={1} value={k} onChange={(e) => setK(Number(e.target.value))} aria-valuetext={t("km.k.text", { k })} data-testid="km-slider"
                 className="mt-2 h-8 w-full cursor-pointer accent-[var(--brand)]" />
          <p className="text-[0.7rem] text-ink-3">{t("km.k.help")}</p>
        </div>
        {report && (
          <dl className="grid grid-cols-3 gap-3 text-xs">
            {([["km.inertia", Math.round(report.inertia).toLocaleString("en"), "km-inertia", "km.inertia.help"], ["km.sil", report.silhouette.toFixed(3), "km-sil", "km.sil.help"], ["km.var", pct(report.variance[0] + report.variance[1]), "km-var", "km.var.help"]] as const).map(([label, v, id2, help]) => (
              <div key={id2} className="rounded-tile bg-inset p-3"><dt className="text-ink-3">{t(label)}</dt><dd className="mt-1 text-lg font-semibold tabular-nums" data-testid={id2}>{v}</dd><dd className="mt-1 hidden text-[0.68rem] leading-snug text-ink-3 sm:block">{t(help)}</dd></div>
            ))}
          </dl>
        )}
      </div>
    </Card>
  );
}

/** Every record on the 2D PCA map, coloured by group; your readings are the red X. */
export function KMap({ report }: { report: KMeansReport }) {
  const { t } = useI18n();
  const W = 640, H = 340, left = 36, bottom = 32, top = 10;
  const m = useMemo(() => {
    const xs = report.points.map((p) => p[0]), ys = report.points.map((p) => p[1]);
    const [x0, x1] = [Math.min(...xs, report.your_point[0]), Math.max(...xs, report.your_point[0])], [y0, y1] = [Math.min(...ys, report.your_point[1]), Math.max(...ys, report.your_point[1])];
    return { sx: linear([x0 - 0.3, x1 + 0.3], [left, W - 8]), sy: linear([y0 - 0.3, y1 + 0.3], [H - bottom, top]), xt: niceTicks(x0, x1, 6), yt: niceTicks(y0, y1, 5) };
  }, [report]);
  return (
    <Card data-testid="km-map">
      <CardHeader icon={<MapIcon />} title={t("km.map.title")} subtitle={t("km.map.sub")} />
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t("km.map.title")} className="h-auto w-full">
        <Axes w={W} h={H} left={left} bottom={bottom} xTicks={m.xt} yTicks={m.yt} sx={m.sx} sy={m.sy} xTitle={`PC1 (${pct(report.variance[0])})`} yTitle={`PC2 (${pct(report.variance[1])})`} />
        {report.points.map(([x, y, c], i) => <circle key={i} cx={m.sx(x)} cy={m.sy(y)} r={2.6} fill={clusterColor(c)} opacity={c === report.your_cluster ? 0.9 : 0.3} />)}
        <YourField x={m.sx(report.your_point[0])} y={m.sy(report.your_point[1])} label={t("farms.yourField")} />
      </svg>
      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-2" data-testid="km-legend">
        {report.clusters.map((c) => <li key={c.cluster} className="flex items-center gap-1.5"><i className="size-2.5 rounded-full" style={{ background: clusterColor(c.cluster) }} />{t("km.group", { n: group(c.cluster) })}</li>)}
        <li className="flex items-center gap-1.5 font-semibold text-coral-ink">✕ {t("farms.yourField")}</li>
      </ul>
      <p className="mt-2 text-xs leading-relaxed text-ink-3">{t("km.map.note")}</p>
    </Card>
  );
}

/** Which group the readings fall in, said in words. */
export function KYours({ report }: { report: KMeansReport }) {
  const { t, locale } = useI18n();
  const mine = report.clusters.find((c) => c.cluster === report.your_cluster)!;
  return (
    <Card data-testid="km-yours" className="flex flex-wrap items-center gap-4">
      <span className="grid size-12 place-items-center rounded-full text-lg font-bold text-[#0b2016]" style={{ background: clusterColor(mine.cluster) }}>{group(mine.cluster)}</span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold" data-testid="km-yours-text">{t("km.yours", { n: group(mine.cluster) })}</p>
        <p className="mt-0.5 flex items-center gap-2 text-xs text-ink-3"><CropGlyph crop={mine.top_crop.key} size={22} />{t("km.yours.crop", { crop: cropName(mine.top_crop, locale), p: pct(mine.share), n: mine.records.toLocaleString("en") })}</p>
      </div>
    </Card>
  );
}

/** Each group's average reading in real units. */
export function KProfiles({ report, features }: { report: KMeansReport; features?: FeatureInfo[] }) {
  const { t, locale } = useI18n();
  const keys = Object.keys(report.clusters[0].averages);
  return (
    <Card data-testid="km-profiles">
      <CardHeader icon={<Table2 />} title={t("km.prof.title")} subtitle={t("km.prof.sub")} />
      <div tabIndex={0} role="region" aria-label={t("km.prof.title")} className="-mx-5 overflow-x-auto px-5 outline-none focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-brand">
        <table className="w-full min-w-[40rem] border-separate border-spacing-0 whitespace-nowrap text-[0.82rem]">
          <thead><tr className="text-left text-xs text-ink-3">
            <th className="px-2 py-2 font-semibold">{t("km.prof.group")}</th><th className="px-2 py-2 font-semibold">{t("km.prof.records")}</th><th className="px-2 py-2 font-semibold">{t("km.prof.top")}</th><th className="px-2 py-2 font-semibold">{t("km.prof.share")}</th>
            {keys.map((f) => <th key={f} className="px-2 py-2 font-semibold">{nameOf(features, f, locale)}</th>)}
          </tr></thead>
          <tbody>
            {report.clusters.map((c) => (
              <tr key={c.cluster} data-testid="km-profile-row" className={c.cluster === report.your_cluster ? "bg-inset" : ""}>
                <th scope="row" className="border-b border-line-2 px-2 py-2 text-left font-semibold"><i className="mr-2 inline-block size-2.5 rounded-full align-middle" style={{ background: clusterColor(c.cluster) }} />{t("km.group", { n: group(c.cluster) })}{c.cluster === report.your_cluster && <Badge tone="mint" className="ml-2">{t("km.you")}</Badge>}</th>
                <td className="border-b border-line-2 px-2 py-2 tabular-nums">{c.records.toLocaleString("en")}</td>
                <td className="border-b border-line-2 px-2 py-2">{cropName(c.top_crop, locale)}</td>
                <td className="border-b border-line-2 px-2 py-2 tabular-nums">{Math.round(c.share * 100)}%</td>
                {keys.map((f) => <td key={f} className="border-b border-line-2 px-2 py-2 tabular-nums">{num(c.averages[f])}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-ink-3">{t("km.prof.note")}</p>
    </Card>
  );
}

/** Records of every crop in every group; darker = more of that crop in that group. */
export function KCrops({ report }: { report: KMeansReport }) {
  const { t, locale } = useI18n();
  const max = Math.max(...report.crop_counts.flat());
  return (
    <Card data-testid="km-crops">
      <CardHeader icon={<Layers />} title={t("km.crops.title")} subtitle={t("km.crops.sub")} />
      <div tabIndex={0} role="region" aria-label={t("km.crops.title")} className="-mx-5 overflow-x-auto px-5 outline-none focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-brand">
        <table className="w-full border-separate border-spacing-1 text-[0.78rem]">
          <thead><tr><th className="px-1" />{report.clusters.map((c) => <th key={c.cluster} scope="col" className="px-1 py-1 text-xs font-semibold text-ink-3">{group(c.cluster)}</th>)}</tr></thead>
          <tbody>
            {report.crops.map((crop, j) => (
              <tr key={crop.key} data-testid="km-crop-row">
                <th scope="row" className="whitespace-nowrap px-1 py-0.5 text-left font-semibold">{cropName(crop, locale)}</th>
                {report.clusters.map((c, i) => {
                  const n = report.crop_counts[i][j];
                  // pale mint with dark text in BOTH themes: a mid-green with either light or dark text fails contrast; empty cells stay plain
                  return n === 0 ? <td key={c.cluster} className="min-w-9 rounded-md bg-inset px-1 py-1 text-center tabular-nums text-ink-3">{n}</td>
                    : <td key={c.cluster} className="min-w-9 rounded-md px-1 py-1 text-center font-semibold tabular-nums text-[#0b2016]" style={{ background: `color-mix(in srgb, #4fc98a ${Math.round(30 + (n / max) * 55)}%, #ffffff)` }}>{n}</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function LineChart({ points, k, title, yTitle, best }: { points: { k: number; v: number }[]; k: number; title: string; yTitle: string; best?: number }) {
  const W = 300, H = 190, left = 44, bottom = 28, top = 10;
  const ys = points.map((p) => p.v), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const sx = linear([2, 10], [left, W - 10]), sy = linear([y0 - (y1 - y0) * 0.08, y1 + (y1 - y0) * 0.08], [H - bottom, top]);
  const yt = niceTicks(y0, y1, 4);
  return (
    <figure>
      <figcaption className="mb-1 text-xs font-semibold text-ink-2">{title}</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={title} className="h-auto w-full">
        <Axes w={W} h={H} left={left} bottom={bottom} xTicks={[2, 4, 6, 8, 10]} yTicks={yt} sx={sx} sy={sy} xTitle="k" yTitle={yTitle} />
        <line x1={sx(k)} x2={sx(k)} y1={top} y2={H - bottom} stroke="#ff5a4f" strokeWidth={1.5} strokeDasharray="3 3" />
        <polyline fill="none" stroke="var(--butter-ink)" strokeWidth={2} points={points.map((p) => `${sx(p.k)},${sy(p.v)}`).join(" ")} />
        {points.map((p) => <circle key={p.k} cx={sx(p.k)} cy={sy(p.v)} r={p.k === best ? 4.5 : 3} fill={p.k === k ? "#ff5a4f" : "var(--butter-ink)"} />)}
      </svg>
    </figure>
  );
}

/** Choosing k: the elbow (inertia) and the silhouette, with the current k marked. */
export function KChoose({ report }: { report: KMeansReport }) {
  const { t } = useI18n();
  return (
    <Card data-testid="km-choose">
      <CardHeader icon={<TrendingDown />} title={t("km.choose.title")} subtitle={t("km.choose.sub")} />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <LineChart title={t("km.elbow")} yTitle={t("km.inertia")} k={report.k} points={report.diagnostics.map((d) => ({ k: d.k, v: d.inertia }))} />
        <LineChart title={t("km.silhouette")} yTitle={t("km.sil")} k={report.k} best={report.best_k} points={report.diagnostics.map((d) => ({ k: d.k, v: d.silhouette }))} />
      </div>
      <p className="mt-3 text-xs leading-relaxed text-ink-3" data-testid="km-choose-note">{t("km.choose.note", { best: report.best_k, k: report.k })}</p>
    </Card>
  );
}


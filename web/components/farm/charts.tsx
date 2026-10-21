"use client";

import { useMemo } from "react";
import type { CropNeeds, FarmsResponse, Readings } from "@/lib/api/client";
import { clusterColor, familyColor, linear, niceTicks, placeLabels } from "@/lib/charts";
import { cropName } from "@/lib/labels";
import { useI18n } from "@/lib/i18n/provider";

const MARK = "#ff5a4f"; // "your field": one fixed warm red on every chart, in both themes

export function YourField({ x, y, label }: { x: number; y: number; label: string }) {
  return (
    <g aria-label={label}>
      <title>{label}</title>
      <circle cx={x} cy={y} r={8} fill="none" stroke={MARK} strokeOpacity={0.35} />
      <path d={`M${x - 4} ${y - 4}l8 8M${x + 4} ${y - 4}l-8 8`} stroke={MARK} strokeWidth={2.4} strokeLinecap="round" />
    </g>
  );
}

export function Axes({ w, h, left, bottom, xTicks, yTicks, sx, sy, xTitle, yTitle }: { w: number; h: number; left: number; bottom: number; xTicks: number[]; yTicks: number[]; sx: (v: number) => number; sy: (v: number) => number; xTitle: string; yTitle: string }) {
  return (
    <g className="fill-ink-3 text-[9px]">
      {yTicks.map((t) => (
        <g key={`y${t}`}>
          <line x1={left} x2={w} y1={sy(t)} y2={sy(t)} stroke="var(--line)" strokeDasharray="1 5" />
          <text x={left - 6} y={sy(t) + 3} textAnchor="end">{t}</text>
        </g>
      ))}
      {xTicks.map((t) => <text key={`x${t}`} x={sx(t)} y={h - bottom + 13} textAnchor="middle">{t}</text>)}
      <text x={(left + w) / 2} y={h - 2} textAnchor="middle">{xTitle}</text>
      <text transform={`translate(8 ${(h - bottom) / 2}) rotate(-90)`} textAnchor="middle">{yTitle}</text>
    </g>
  );
}

/** Every record as a dot at its rainfall (x) and temperature (y), coloured by K-Means group; your own field is the red X. */
export function FarmsChart({ data, yours, xTitle, yTitle, yourLabel }: { data: FarmsResponse; yours?: Readings; xTitle: string; yTitle: string; yourLabel: string }) {
  const W = 330, H = 214, left = 34, bottom = 30, top = 8;
  const { sx, sy, xTicks, yTicks } = useMemo(() => {
    const xs = data.points.map((p) => p[0]), ys = data.points.map((p) => p[1]);
    const [x0, x1, y0, y1] = [Math.min(...xs, yours?.rainfall ?? Infinity), Math.max(...xs, yours?.rainfall ?? -Infinity), Math.min(...ys, yours?.temperature ?? Infinity), Math.max(...ys, yours?.temperature ?? -Infinity)];
    const padX = (x1 - x0) * 0.04, padY = (y1 - y0) * 0.06;
    return { sx: linear([x0 - padX, x1 + padX], [left, W - 6]), sy: linear([y0 - padY, y1 + padY], [H - bottom, top]), xTicks: niceTicks(x0, x1, 4), yTicks: niceTicks(y0, y1, 4) };
  }, [data, yours]);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${yTitle} / ${xTitle}`} className="h-auto w-full">
      <Axes w={W} h={H} left={left} bottom={bottom} xTicks={xTicks} yTicks={yTicks} sx={sx} sy={sy} xTitle={xTitle} yTitle={yTitle} />
      {data.points.map(([x, y, c], i) => <circle key={i} cx={sx(x)} cy={sy(y)} r={2.6} fill={clusterColor(c)} opacity={0.85} />)}
      {yours && <YourField x={sx(yours.rainfall)} y={sy(yours.temperature)} label={yourLabel} />}
    </svg>
  );
}

/** Average temperature (x) against rainfall (y) of every crop. Colour = crop family, bubble size = humidity. */
export function NeedsChart({ data, yours, xTitle, yTitle, yourLabel }: { data: CropNeeds[]; yours?: Readings; xTitle: string; yTitle: string; yourLabel: string }) {
  const { locale } = useI18n();
  const W = 330, H = 214, left = 38, bottom = 30, top = 10;
  const model = useMemo(() => {
    const t = data.map((d) => d.temperature), r = data.map((d) => d.rainfall);
    const [x0, x1, y1] = [Math.min(...t, yours?.temperature ?? Infinity) - 1.2, Math.max(...t, yours?.temperature ?? -Infinity) + 1.2, Math.max(...r, yours?.rainfall ?? -Infinity) * 1.1];
    const sx = linear([x0, x1], [left, W - 8]), sy = linear([0, y1], [H - bottom, top]);
    const maxH = Math.max(...data.map((d) => d.humidity));
    const bubbles = data.map((d) => ({ d, x: sx(d.temperature), y: sy(d.rainfall), r: 4.5 + 5.5 * Math.sqrt(d.humidity / maxH) }));
    // label the biggest-rainfall crops first so the busy middle is the part that loses labels
    const order = bubbles.map((_, i) => i).sort((a, b) => bubbles[b].d.rainfall - bubbles[a].d.rainfall);
    const labels = placeLabels(order.map((i) => ({ x: bubbles[i].x, y: bubbles[i].y, r: bubbles[i].r, text: cropName(bubbles[i].d.crop, locale) })), W, H).map((l) => ({ ...l, index: order[l.index] }));
    return { sx, sy, bubbles, labels, xTicks: niceTicks(x0, x1, 4), yTicks: niceTicks(0, y1, 3) };
  }, [data, yours, locale]);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${yTitle} / ${xTitle}`} className="h-auto w-full">
      <Axes w={W} h={H} left={left} bottom={bottom} xTicks={model.xTicks} yTicks={model.yTicks} sx={model.sx} sy={model.sy} xTitle={xTitle} yTitle={yTitle} />
      {model.bubbles.map(({ d, x, y, r }) => (
        <circle key={d.crop.key} cx={x} cy={y} r={r} fill={familyColor(d.crop.family)} fillOpacity={0.4} stroke={familyColor(d.crop.family)} strokeWidth={1.3}>
          <title>{`${cropName(d.crop, locale)}: ${d.temperature.toFixed(1)} °C · ${Math.round(d.rainfall)} mm`}</title>
        </circle>
      ))}
      {model.labels.map((l) => <text key={l.index} x={l.x} y={l.y} textAnchor={l.anchor} className="fill-ink text-[9px] font-semibold">{cropName(model.bubbles[l.index].d.crop, locale)}</text>)}
      {yours && <YourField x={model.sx(yours.temperature)} y={model.sy(yours.rainfall)} label={yourLabel} />}
    </svg>
  );
}

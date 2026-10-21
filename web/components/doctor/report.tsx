"use client";

import { CloudSun, FlaskConical, Lightbulb, TriangleAlert, Stethoscope } from "lucide-react";
import Link from "next/link";
import { Badge, STATUS_TONE } from "@/components/ui/badge";
import { Card, CardHeader } from "@/components/ui/card";
import { Gauge } from "@/components/ui/gauge";
import type { DoctorResponse } from "@/lib/api/client";
import { useMeta, withCheck } from "@/lib/data";
import { useI18n } from "@/lib/i18n/provider";
import { cropName, featureLabel, rangeText, readingText } from "@/lib/labels";
import { featureRange, STATUS_KEY } from "@/components/home/format";
import type { MessageKey } from "@/lib/i18n/dictionaries";

const NUTRIENTS = ["N", "P", "K", "ph"];
const WEATHER = ["temperature", "humidity", "rainfall"];
const RING = { good: "var(--mint)", moderate: "var(--butter)", attention: "var(--coral)" } as const;

/** One reading on its gauge: the measured value, the crop's usual range, and the status in words. */
function Row({ r }: { r: DoctorResponse["readings"][number] }) {
  const { t, locale } = useI18n();
  const meta = useMeta().data;
  const f = meta?.features.find((x) => x.key === r.feature);
  const { min, max } = featureRange(meta?.features, r.feature);
  const name = featureLabel(meta?.features, r.feature, locale);
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-2 border-b md:grid-cols-[9.5rem_1fr_8.5rem] md:gap-4 border-dashed border-line py-3 last:border-0" data-testid={`row-${r.feature}`}>
      <div>
        <p className="text-sm font-semibold">{name}</p>
        <p className="text-xs text-ink-3">{t("doctor.yours", { v: readingText(r.value, f) })}</p>
      </div>
      <div className="order-last col-span-2 md:order-none md:col-span-1">
        <Gauge value={r.value} low={r.low} high={r.high} min={min} max={max} status={r.status} label={`${name}: ${t(STATUS_KEY[r.status])}`} />
        <div className="mt-2 flex justify-between text-[0.68rem] text-ink-3"><span>{readingText(min, f)}</span><em className="not-italic font-semibold text-ink-2">{t("doctor.usual", { range: rangeText(r.low, r.high, f) })}</em><span>{readingText(max, f)}</span></div>
      </div>
      <Badge tone={STATUS_TONE[r.status]} className="justify-self-end">{t(STATUS_KEY[r.status])}</Badge>
    </div>
  );
}

/** Overall soil health as a ring, with the count of readings inside the usual range. */
export function OverallCard({ report, checkId }: { report: DoctorResponse; checkId?: number }) {
  const { t, locale } = useI18n();
  const meta = useMeta().data;
  const inRange = report.readings.filter((r) => r.status === "good").length;
  const crop = cropName(report.crop, locale);
  const pct = report.score * 100;
  const circ = 2 * Math.PI * 50;
  return (
    <Card data-testid="overall">
      <CardHeader icon={<Stethoscope />} title={t("doctor.overall.title")} subtitle={crop} />
      <div className="relative mx-auto my-3 w-44">
        <svg viewBox="0 0 120 120" className="block w-full" role="img" aria-label={`${t("doctor.overall.title")}: ${Math.round(pct)}%`}>
          <circle cx="60" cy="60" r="50" fill="none" stroke="var(--track)" strokeWidth="10" />
          <circle cx="60" cy="60" r="50" fill="none" stroke={RING[report.overall]} strokeWidth="10" strokeLinecap="round" strokeDasharray={`${(pct / 100) * circ} ${circ}`} transform="rotate(-90 60 60)" />
        </svg>
        <div className="absolute inset-0 grid place-content-center text-center">
          <b className="text-[2.2rem] font-light leading-none tracking-[-0.04em] tabular-nums" data-testid="score">{Math.round(pct)}%</b>
          <span className="mt-1 text-[0.68rem] text-ink-3">{t("doctor.overall.in", { n: inRange })}</span>
        </div>
      </div>
      <div className="text-center"><Badge tone={STATUS_TONE[report.overall]} className="px-3.5 py-1 text-[0.8rem]">{t(STATUS_KEY[report.overall])}</Badge></div>
      <div className="mt-4 flex gap-1.5" aria-hidden="true">{report.readings.map((r) => <i key={r.feature} className="h-2 flex-1 rounded-full" style={{ background: RING[r.status] }} title={featureLabel(meta?.features, r.feature, locale)} />)}</div>
      <p className="mt-4 text-center text-xs leading-relaxed text-ink-3">
        {report.needs_attention > 0 ? t("doctor.overall.bad", { n: report.needs_attention, crop }) : t("doctor.overall.ok", { crop })}
      </p>
      {report.overall !== "good" && (
        <Link href={withCheck(`/${locale}/plan-b/`, checkId)} className="mt-3 flex justify-center text-xs font-semibold text-mint-ink">{t("doctor.overall.see")} →</Link>
      )}
    </Card>
  );
}

export function GaugesCard({ report, group }: { report: DoctorResponse; group: "nutrients" | "weather" }) {
  const { t } = useI18n();
  const keys = group === "nutrients" ? NUTRIENTS : WEATHER;
  return (
    <Card data-testid={group}>
      <CardHeader icon={group === "nutrients" ? <FlaskConical /> : <CloudSun />} title={t(group === "nutrients" ? "doctor.nutrients" : "doctor.weather")} />
      {report.readings.filter((r) => keys.includes(r.feature)).map((r) => <Row key={r.feature} r={r} />)}
    </Card>
  );
}

/** What a farmer can do about each reading that is off. The wording lives in the dictionaries so it follows the language. */
export function TipsCard({ report }: { report: DoctorResponse }) {
  const { t, locale } = useI18n();
  const meta = useMeta().data;
  const tips = report.readings.filter((r) => r.status !== "good" && r.tip_key);
  return (
    <Card data-testid="tips">
      <CardHeader icon={<Lightbulb />} title={t("doctor.do.title")} subtitle={t("doctor.do.sub")} action={tips.length > 0 && <Badge tone="lavender">{t("doctor.do.count", { n: tips.length })}</Badge>} />
      {tips.length === 0 ? <p className="rounded-tile bg-inset p-4 text-sm text-ink-2">{t("doctor.do.none")}</p> : (
        <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {tips.map((r) => (
            <li key={r.feature} className="flex gap-3 rounded-2xl bg-inset p-3.5 shadow-[inset_0_0_0_1px_var(--line-2)]">
              <span className={`grid size-9 shrink-0 place-items-center rounded-xl [&>svg]:size-[1.1rem] ${r.status === "attention" ? "bg-coral/16 text-coral-ink" : "bg-butter/24 text-butter-ink"}`}><TriangleAlert /></span>
              <div>
                <p className="flex flex-wrap items-center gap-2 text-sm font-semibold">{featureLabel(meta?.features, r.feature, locale)}<Badge tone={STATUS_TONE[r.status]}>{t(r.direction === "high" ? "doctor.dir.high" : "doctor.dir.low")}</Badge></p>
                <p className="mt-1 text-[0.8rem] leading-relaxed text-ink-2">{t(`tip.${r.tip_key}` as MessageKey)}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-4 text-xs text-ink-3">{t("doctor.do.confirm")}</p>
    </Card>
  );
}

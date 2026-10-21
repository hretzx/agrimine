"use client";

import { Columns3, X } from "lucide-react";
import { CropGlyph } from "@/components/farm/crop-glyph";
import { Card, CardHeader } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { ErrorState, Loading } from "@/components/ui/states";
import type { Readings } from "@/lib/api/client";
import { useDoctors, useMeta } from "@/lib/data";
import { useI18n } from "@/lib/i18n/provider";
import { cropName, featureLabel, rangeText, readingText } from "@/lib/labels";

const MARK = { good: { char: "✓", cls: "text-mint-ink", key: "mark.inside" }, moderate: { char: "~", cls: "text-butter-ink", key: "mark.near" }, attention: { char: "✗", cls: "text-coral-ink", key: "mark.outside" } } as const;

/** Usual range of each chosen crop for every reading, next to your own value. Used by What should I grow? and Plan B. */
export function CompareTable({ readings, crops, onChange, title, subtitle, testId, max = 4 }: { readings: Readings; crops: string[]; onChange?: (next: string[]) => void; title: string; subtitle: string; testId: string; max?: number }) {
  const { t, locale } = useI18n();
  const meta = useMeta().data;
  const reports = useDoctors(readings, crops);
  const data = reports.data;
  const label = (key: string) => { const c = meta?.crops.find((x) => x.key === key); return c ? cropName(c, locale) : key; };
  const addable = (meta?.crops ?? []).filter((c) => !crops.includes(c.key)).map((c) => ({ value: c.key, label: cropName(c, locale) }));
  return (
    <Card data-testid={testId}>
      <CardHeader icon={<Columns3 />} title={title} subtitle={subtitle} />
      {onChange && (
        <div className="mb-4 flex flex-wrap items-end gap-2.5">
          {crops.map((c) => (
            <span key={c} className="inline-flex items-center gap-2 rounded-full bg-inset py-1 pl-1.5 pr-1 text-sm font-semibold shadow-[inset_0_0_0_1px_var(--line)]">
              <CropGlyph crop={c} size={26} round />{label(c)}
              <button type="button" aria-label={t("grow.compare.remove", { crop: label(c) })} onClick={() => onChange(crops.filter((x) => x !== c))} disabled={crops.length <= 1} className="grid size-10 place-items-center rounded-full sm:size-6 text-ink-3 outline-none hover:bg-card focus-visible:outline-2 focus-visible:outline-brand disabled:opacity-30 [&>svg]:size-3.5"><X /></button>
            </span>
          ))}
          {crops.length < max && addable.length > 0 && <Select label={t("grow.compare.add")} placeholder={t("grow.compare.choose")} value="" onChange={(v) => onChange([...crops, v])} options={addable} className="min-w-[11rem]" />}
          {crops.length >= max && <span className="text-xs text-ink-3">{t("grow.compare.max")}</span>}
        </div>
      )}
      {reports.error ? <ErrorState onRetry={() => reports.mutate()} /> : !data ? <Loading className="h-48" /> : (
        <div tabIndex={0} role="region" aria-label={String(title)} className="-mx-5 overflow-x-auto px-5 outline-none focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-brand">
        <table className="w-full min-w-[34rem] border-separate border-spacing-0 whitespace-nowrap text-[0.85rem]">
          <thead>
            <tr className="text-left text-xs text-ink-3">
              <th className="px-3 py-2 font-semibold" />
              <th className="px-3 py-2 font-semibold">{t("grow.compare.yours")}</th>
              {crops.map((c) => <th key={c} className="px-3 py-2 font-semibold">{label(c)}</th>)}
            </tr>
          </thead>
          <tbody>
            {data[0].readings.map((row, i) => {
              const f = meta?.features.find((x) => x.key === row.feature);
              return (
                <tr key={row.feature}>
                  <th scope="row" className="border-b border-line-2 px-3 py-2.5 text-left font-semibold">{featureLabel(meta?.features, row.feature, locale)}</th>
                  <td className="border-b border-line-2 bg-inset px-3 py-2.5 font-bold tabular-nums">{readingText(row.value, f)}</td>
                  {data.map((rep, j) => {
                    const r = rep.readings[i];
                    const m = MARK[r.status];
                    return (
                      <td key={crops[j]} className="border-b border-line-2 px-3 py-2.5 tabular-nums">
                        {rangeText(r.low, r.high, f)}
                        <span className={`ml-2 font-bold ${m.cls}`} role="img" aria-label={t(m.key)}>{m.char}</span>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
        </div>
      )}
    </Card>
  );
}

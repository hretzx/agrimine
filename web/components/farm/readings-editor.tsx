"use client";

import { RotateCcw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import { useI18n } from "@/lib/i18n/provider";
import { readingProblem, STEPS } from "@/lib/readings";
import { rangeText } from "@/lib/labels";
import type { ReadingsState } from "@/lib/use-readings";

/** The seven boxes a visitor can edit to try values out. Shared by What should I grow?, Crop Doctor and Plan B. */
export function ReadingsEditor({ state }: { state: ReadingsState }) {
  const { t, locale } = useI18n();
  const { features, text, setText, edited, reset, check } = state;
  return (
    <Card data-testid="readings">
      <CardHeader
        title={t("readings.title")}
        subtitle={check ? t("readings.sub.check", { id: check.id }) : t("readings.sub.none")}
        action={
          <div className="flex flex-wrap items-center justify-end gap-2">
            {edited && <Badge tone="butter">{t("readings.edited")}</Badge>}
            <Button variant="outline" onClick={reset} disabled={!edited} className="px-3 py-3 text-xs sm:py-1.5 [&>svg]:size-3.5"><RotateCcw />{t("readings.reset")}</Button>
          </div>
        }
      />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
        {features.map((f) => {
          const label = locale === "mr" ? f.label_mr : f.label;
          const problem = readingProblem(f, text[f.key] ?? "");
          const id = `reading-${f.key}`;
          return (
            <div key={f.key}>
              <label htmlFor={id} className="mb-1 block truncate text-[0.72rem] font-semibold text-ink-3" title={label}>{label}{f.unit && ` (${f.unit})`}</label>
              <input
                id={id}
                type="number"
                inputMode="decimal"
                step={STEPS[f.key] ?? "any"}
                min={f.lo}
                max={f.hi}
                value={text[f.key] ?? ""}
                onChange={(e) => setText(f.key, e.target.value)}
                aria-invalid={problem ? true : undefined}
                aria-describedby={`${id}-hint`}
                className={cn("w-full rounded-xl bg-inset px-3 py-2 text-[16px] font-semibold tabular-nums sm:text-[0.95rem] outline-none shadow-[inset_0_0_0_1px_var(--line)] focus-visible:shadow-[inset_0_0_0_2px_var(--brand)]", problem && "shadow-[inset_0_0_0_2px_var(--coral)]")}
              />
              <p id={`${id}-hint`} className={cn("mt-1 truncate text-[0.66rem]", problem ? "font-medium text-coral-ink" : "text-ink-3")}>
                {problem ? t("check.err.range", { lo: f.lo, hi: f.hi }) : rangeText(f.lo, f.hi, f)}
              </p>
            </div>
          );
        })}
      </div>
      {!state.valid && <p role="alert" className="mt-3 text-sm font-medium text-coral-ink">{t("readings.fix")}</p>}
    </Card>
  );
}

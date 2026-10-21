"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { mutate } from "swr";
import { AppShell } from "@/components/farm/app-shell";
import { PageHeader } from "@/components/home/header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ErrorState, Loading } from "@/components/ui/states";
import { api, ApiError, type FeatureInfo, type Readings } from "@/lib/api/client";
import { cn } from "@/lib/cn";
import { useMeta, useRecentChecks } from "@/lib/data";
import { useI18n } from "@/lib/i18n/provider";
import { rangeText } from "@/lib/labels";
import { readingProblem as problem, STEPS as STEP } from "@/lib/readings";

export default function NewCheck() {
  const { t, locale } = useI18n();
  const router = useRouter();
  const meta = useMeta();
  const latest = useRecentChecks(1).data?.[0];
  const [typed, setTyped] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [failed, setFailed] = useState(false);

  const features = meta.data?.features ?? [];
  const valueOf = (f: FeatureInfo) => typed[f.key] ?? (latest ? String(latest.values[f.key as keyof Readings]) : "");

  async function submit(e: FormEvent) {
    e.preventDefault();
    const next: Record<string, string> = {};
    for (const f of features) {
      const p = problem(f, valueOf(f));
      if (p) next[f.key] = p === "required" ? t("check.err.required") : p === "number" ? t("check.err.number") : t("check.err.range", { lo: f.lo, hi: f.hi });
    }
    setErrors(next);
    if (Object.keys(next).length) return;
    setSaving(true);
    setFailed(false);
    try {
      const values = Object.fromEntries(features.map((f) => [f.key, Number(valueOf(f))])) as Readings;
      const saved = await api.createCheck(values);
      await mutate(() => true, undefined, { revalidate: true }); // counts, recent checks and the sidebar now know about the new check
      router.push(`/${locale}/?check=${saved.id}`);
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fields).length) setErrors(err.fields);
      else setFailed(true);
      setSaving(false);
    }
  }

  return (
    <AppShell active="home">
      <PageHeader title={t("check.title")} subtitle={t("check.sub")} />
      <Card className="max-w-4xl">
        {meta.error ? <ErrorState onRetry={() => meta.mutate()} /> : !meta.data ? <Loading className="h-64" /> : (
          <form onSubmit={submit} noValidate data-testid="check-form">
            <div className="grid grid-cols-2 gap-x-4 gap-y-5 sm:grid-cols-4">
              {features.map((f) => {
                const label = locale === "mr" ? f.label_mr : f.label;
                const id = `field-${f.key}`;
                const err = errors[f.key];
                return (
                  <div key={f.key}>
                    <label htmlFor={id} className="mb-1.5 block text-xs font-semibold text-ink-2">{label}{f.unit && <span className="font-normal text-ink-3"> ({f.unit})</span>}</label>
                    <input
                      id={id}
                      name={f.key}
                      type="number"
                      inputMode="decimal"
                      step={STEP[f.key] ?? "any"}
                      min={f.lo}
                      max={f.hi}
                      value={valueOf(f)}
                      onChange={(e) => setTyped((s) => ({ ...s, [f.key]: e.target.value }))}
                      aria-invalid={err ? true : undefined}
                      aria-describedby={`${id}-hint`}
                      className={cn("w-full rounded-xl bg-inset px-3 py-2.5 text-[16px] font-semibold tabular-nums sm:text-[0.95rem] outline-none shadow-[inset_0_0_0_1px_var(--line)] focus-visible:shadow-[inset_0_0_0_2px_var(--brand)]", err && "shadow-[inset_0_0_0_2px_var(--coral)]")}
                    />
                    <p id={`${id}-hint`} className={cn("mt-1 text-[0.7rem]", err ? "font-medium text-coral-ink" : "text-ink-3")}>
                      {err ?? rangeText(f.lo, f.hi, f)}
                    </p>
                  </div>
                );
              })}
            </div>
            {Object.keys(errors).length > 0 && <p role="alert" className="mt-4 text-sm font-medium text-coral-ink">{t("check.invalid")}</p>}
            {failed && <div className="mt-4"><ErrorState /></div>}
            <div className="mt-6 flex items-center gap-3">
              <Button type="submit" disabled={saving}>{saving ? t("check.saving") : t("check.save")}</Button>
            </div>
          </form>
        )}
      </Card>
    </AppShell>
  );
}

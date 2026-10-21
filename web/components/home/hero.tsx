"use client";

import { ArrowUpRight, CloudRain, FlaskConical, Sparkles, Thermometer, Check } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { CropGlyph } from "@/components/farm/crop-glyph";
import { Badge } from "@/components/ui/badge";
import { ButtonLink } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ErrorState, Loading } from "@/components/ui/states";
import type { CheckOut } from "@/lib/api/client";
import { useMeta, useRecommendation, withCheck } from "@/lib/data";
import { useI18n } from "@/lib/i18n/provider";
import { cropName, featureLabel, readingText } from "@/lib/labels";
import { Scenery } from "./scenery";

function Mini({ icon, value, label }: { icon: ReactNode; value: string; label: string }) {
  return (
    <div data-testid="hero-mini" className="@container min-w-0 rounded-tile bg-inset px-2 py-2.5 shadow-[inset_0_0_0_1px_var(--line-2)]">
      <p className="flex items-center gap-1.5 whitespace-nowrap text-sm font-semibold tracking-tight">
        <span className="text-ink-3 @max-[4.8rem]:hidden [&>svg]:size-[0.95rem]">{icon}</span>
        {value}
      </p>
      <p data-testid="hero-mini-label" className="mt-0.5 text-[0.68rem] leading-tight text-ink-3">{label}</p>
    </div>
  );
}

/** The most prominent card: the recommended crop for the current check, how sure the model is, and the three key readings. */
export function Hero({ check, empty }: { check?: CheckOut; empty?: boolean }) {
  const { t, locale } = useI18n();
  const meta = useMeta().data;
  const rec = useRecommendation(check?.values);
  const feature = (key: string) => meta?.features.find((f) => f.key === key);

  if (empty) {
    return (
      <Card className="grid min-h-[17rem] place-items-center text-center">
        <div className="max-w-sm space-y-4">
          <p className="text-lg font-semibold tracking-tight">{t("hero.title")}</p>
          <p className="text-sm text-ink-3">{t("hero.empty")}</p>
          <ButtonLink href={`/${locale}/check/`}>{t("action.newCheck")}</ButtonLink>
        </div>
      </Card>
    );
  }
  const data = rec.data;
  return (
    <Card className="p-0" data-testid="hero">
      <div className="relative h-[7.6rem] overflow-hidden rounded-t-card">
        <Scenery />
        <div className="absolute inset-x-[1.1rem] top-4 z-[2] flex items-start justify-between">
          <Badge tone="ink"><Sparkles />{t("hero.badge")}</Badge>
          <Link href={withCheck(`/${locale}/grow/`, check?.id)} aria-label={t("action.openDetails")} className="grid size-10 sm:size-[2.125rem] place-items-center rounded-full bg-card text-ink shadow-float outline-none focus-visible:outline-2 focus-visible:outline-brand [&>svg]:size-4">
            <ArrowUpRight />
          </Link>
        </div>
      </div>
      <div className="px-5 pb-5">
        {rec.error ? <ErrorState onRetry={() => rec.mutate()} /> : !data || !check ? <Loading className="mt-4 h-40" /> : (
          <div className="grid grid-cols-[7rem_minmax(0,1fr)] gap-5">
            <span className="relative z-[3] -mt-[3.25rem] grid size-28 place-items-center self-start rounded-full bg-gradient-to-br from-[#fff8e1] to-[#f4e3a8] shadow-[0_0_0_5px_var(--scene-ring),0_16px_28px_-12px_rgb(0_0_0/.35)]">
              <CropGlyph crop={data.best.key} size={76} round className="!bg-transparent !shadow-none" />
            </span>
            <div className="min-w-0 pt-3.5">
              <h3 className="flex flex-wrap items-center gap-3 text-[2rem] font-light leading-none tracking-[-0.04em] sm:text-[2.4rem]" data-testid="hero-crop">
                {cropName(data.best, locale)}
                <Badge tone="mint" className="text-xs tracking-normal"><Check />{t("level.strong")}</Badge>
              </h3>
              <div className="mt-2.5 flex items-baseline gap-3.5">
                <span className="text-[2.1rem] font-light leading-none tracking-[-0.04em] tabular-nums" data-testid="hero-probability">{(data.probability * 100).toFixed(1)}%</span>
                <span className="text-xs leading-snug text-ink-3">{t("hero.prob")}<br />{data.agrees ? t("hero.treeAgrees") : t("hero.treeDiffers", { crop: cropName(data.id3, locale) })}</span>
              </div>
              <div className="mt-4 grid grid-cols-3 gap-2">
                {(["ph", "temperature", "rainfall"] as const).map((key) => (
                  <Mini key={key} icon={key === "ph" ? <FlaskConical /> : key === "temperature" ? <Thermometer /> : <CloudRain />} value={readingText(check.values[key], feature(key))} label={featureLabel(meta?.features, key, locale)} />
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}

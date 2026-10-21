"use client";

import { Check, GitFork, Sparkles, Target } from "lucide-react";
import { CropGlyph } from "@/components/farm/crop-glyph";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader } from "@/components/ui/card";
import { Track } from "@/components/ui/track";
import type { Recommendation } from "@/lib/api/client";
import { useI18n } from "@/lib/i18n/provider";
import { cropName } from "@/lib/labels";
import { Scenery } from "@/components/home/scenery";
import { pct } from "@/components/home/format";

/** The answer: the best crop with the model's probability. */
export function RecommendedCard({ rec }: { rec: Recommendation }) {
  const { t, locale } = useI18n();
  return (
    <Card className="p-0" data-testid="recommended">
      <div className="relative h-[6.5rem] overflow-hidden rounded-t-card">
        <Scenery />
        <div className="absolute left-[1.1rem] top-4 z-[2]"><Badge tone="ink"><Sparkles />{t("grow.badge")}</Badge></div>
      </div>
      <div className="grid grid-cols-[6.5rem_minmax(0,1fr)] gap-5 px-5 pb-5">
        <span className="relative z-[3] -mt-[3rem] grid size-[6.5rem] place-items-center self-start rounded-full bg-gradient-to-br from-[#fff8e1] to-[#f4e3a8] shadow-[0_0_0_5px_var(--scene-ring),0_16px_28px_-12px_rgb(0_0_0/.35)]">
          <CropGlyph crop={rec.best.key} size={70} round className="!bg-transparent !shadow-none" />
        </span>
        <div className="min-w-0 pt-3">
          <h2 className="flex flex-wrap items-center gap-3 text-[2.2rem] font-light leading-none tracking-[-0.04em]" data-testid="grow-best">
            {cropName(rec.best, locale)}
            <Badge tone="mint" className="text-xs tracking-normal"><Check />{t("level.strong")}</Badge>
          </h2>
          <div className="mt-2.5 flex items-baseline gap-3.5">
            <span className="text-[2rem] font-light leading-none tracking-[-0.04em] tabular-nums" data-testid="grow-probability">{pct(rec.probability)}</span>
            <span className="text-xs leading-snug text-ink-3">{t("hero.prob")}</span>
          </div>
        </div>
      </div>
    </Card>
  );
}

/** ID3's second opinion, and how pure the leaf it ended in was. */
export function TreeCard({ rec }: { rec: Recommendation }) {
  const { t, locale } = useI18n();
  return (
    <Card data-testid="tree">
      <CardHeader icon={<GitFork />} title={t("grow.tree.title")} subtitle={t("grow.tree.sub")} action={<Badge tone={rec.agrees ? "mint" : "butter"}>{rec.agrees ? t("grow.tree.agrees") : t("grow.tree.differs")}</Badge>} />
      <p className="text-[2rem] font-light leading-none tracking-[-0.04em]">{cropName(rec.id3, locale)}</p>
      <p className="mt-3 text-xs leading-relaxed text-ink-3">{t("grow.tree.purity", { p: `${Math.round(rec.id3_purity * 100)}%` })}</p>
      <Track hatch value={rec.id3_purity * 100} label={`${t("grow.tree.title")}: ${Math.round(rec.id3_purity * 100)}%`} color="linear-gradient(90deg,#f4cf58,#e9b22e)" className="mt-3 [&>div]:h-2.5" />
    </Card>
  );
}

/** The best crop's profile-match score, and the next best crop for comparison. */
export function MatchCard({ rec }: { rec: Recommendation }) {
  const { t, locale } = useI18n();
  const best = rec.ranking.find((r) => r.crop.key === rec.best.key)!;
  const next = rec.similar[0];
  return (
    <Card data-testid="match">
      <CardHeader icon={<Target />} title={t("grow.match.title")} subtitle={t("grow.match.sub")} />
      <p className="text-[2rem] font-light leading-none tracking-[-0.04em] tabular-nums">{Math.round(best.match)}<span className="text-lg font-normal text-ink-3"> / 100</span></p>
      <p className="mt-3 text-xs leading-relaxed text-ink-3">{t("grow.match.note")}</p>
      <Track value={best.match} label={`${t("grow.match.title")}: ${Math.round(best.match)}`} color="linear-gradient(90deg,var(--mint),#2fb573)" className="mt-3 [&>div]:h-2.5" />
      {next && <p className="mt-3 text-[0.78rem] font-medium text-ink-2">{t("grow.match.next", { crop: cropName(next.crop, locale), score: Math.round(next.match) })}</p>}
    </Card>
  );
}

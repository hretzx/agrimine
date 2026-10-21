"use client";

import { ListOrdered } from "lucide-react";
import { useState } from "react";
import { CropGlyph } from "@/components/farm/crop-glyph";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { Track } from "@/components/ui/track";
import type { Recommendation } from "@/lib/api/client";
import { useI18n } from "@/lib/i18n/provider";
import { cropName } from "@/lib/labels";
import { LEVEL, pct } from "@/components/home/format";

const FIRST = 8;

/** Every crop, most likely first. The bar and the number are the separate profile-match score; the percentage is the model's probability. */
export function RankingCard({ rec }: { rec: Recommendation }) {
  const { t, locale } = useI18n();
  const [all, setAll] = useState(false);
  const rows = all ? rec.ranking : rec.ranking.slice(0, FIRST);
  return (
    <Card data-testid="ranking">
      <CardHeader icon={<ListOrdered />} title={t("grow.rank.title")} subtitle={t("grow.rank.sub")} action={<Badge tone="lavender">{rows.length} / {rec.ranking.length}</Badge>} />
      <ol className="flex flex-col gap-1.5">
        {rows.map((r, i) => {
          const level = i === 0 ? ({ key: "top3.best", tone: "mint", color: "var(--mint)" } as const) : LEVEL[r.level];
          return (
            <li key={r.crop.key} className={`grid grid-cols-[1.4rem_2.2rem_minmax(0,1fr)_auto] items-center gap-3 rounded-xl px-2 py-1.5 md:grid-cols-[1.4rem_2.2rem_minmax(0,1fr)_auto_3rem_3.6rem] ${i === 0 ? "bg-inset shadow-[inset_0_0_0_1px_var(--line-2)]" : ""}`}>
              <span className="text-center text-xs font-bold text-ink-3">{i + 1}</span>
              <CropGlyph crop={r.crop.key} size={34} />
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold">{cropName(r.crop, locale)}</p>
                <Track value={r.match} label={`${cropName(r.crop, locale)}: ${Math.round(r.match)}`} color={level.color} className="mt-1 [&>div]:h-1.5" />
              </div>
              <Badge tone={level.tone} className="hidden md:inline-flex">{t(level.key)}</Badge>
              <span className="grid place-items-center rounded-lg bg-card px-2 py-1 text-sm font-semibold tabular-nums shadow-[0_0_0_1px_var(--line)]">{Math.round(r.match)}</span>
              <span className="hidden text-right text-[0.78rem] font-semibold tabular-nums text-ink-3 md:block" title={t("grow.rank.prob")}>{pct(r.probability)}</span>
            </li>
          );
        })}
      </ol>
      {rec.ranking.length > FIRST && (
        <Button variant="ghost" onClick={() => setAll((v) => !v)} className="mt-3 px-3 py-3 text-xs sm:py-1.5" aria-expanded={all}>
          {all ? t("grow.rank.showLess") : t("grow.rank.showAll", { n: rec.ranking.length })}
        </Button>
      )}
    </Card>
  );
}

import type { ReactNode } from "react";
import { Badge, type Tone } from "@/components/ui/badge";
import { Track } from "@/components/ui/track";
import { CropGlyph } from "./crop-glyph";

/** One crop with a similarity bar, a status pill and its score (Top 3, Plan B, the full ranking). */
export function CropRow({
  crop, name, subtitle, score, tone, tag, color, trailing,
}: {
  crop: string; name: string; subtitle?: string; score: number; tone: Tone; tag: string; color: string; trailing?: ReactNode;
}) {
  return (
    <div className="flex items-center gap-3 rounded-tile bg-inset p-2 pr-2.5 shadow-[inset_0_0_0_1px_var(--line-2)]">
      <CropGlyph crop={crop} size={40} />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold tracking-tight">{name}</p>
        {subtitle && <p className="whitespace-nowrap text-[0.72rem] text-ink-3">{subtitle}</p>}
        <Track value={score} label={`${name}: ${Math.round(score)}`} color={color} className="mt-1.5 [&>div]:h-1.5" />
      </div>
      <Badge tone={tone}>{tag}</Badge>
      <span className="grid min-w-[3.5rem] place-items-center rounded-xl bg-card px-2.5 py-2 text-base font-semibold tracking-tight shadow-[0_0_0_1px_var(--line),0_2px_6px_-2px_rgb(0_0_0/.18)]">
        {Math.round(score)}
      </span>
      {trailing}
    </div>
  );
}

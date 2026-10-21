import { Leaf } from "lucide-react";
import { cn } from "@/lib/cn";
import { GLYPHS, GLYPH_TINT } from "./glyph-data";

/** A crop drawn on a soft tinted tile. All 22 crops have a drawing; a crop added later without one shows a neutral leaf (never another crop's picture). */
export function CropGlyph({ crop, size = 40, round = false, className }: { crop: string; size?: number; round?: boolean; className?: string }) {
  const body = GLYPHS[crop];
  return (
    <span
      aria-hidden="true"
      className={cn("grid shrink-0 place-items-center shadow-[inset_0_1px_0_rgb(255_255_255/.35),0_0_0_1px_var(--line)] dark:brightness-95", round ? "rounded-full" : "rounded-[0.7rem]", !body && "bg-inset text-ink-3", className)}
      style={{ width: `${size / 16}rem`, height: `${size / 16}rem`, background: body ? GLYPH_TINT[crop] : undefined }}
    >
      {body ? (
        <svg viewBox="0 0 32 32" className="size-[62%]" dangerouslySetInnerHTML={{ __html: body }} />
      ) : (
        <Leaf className="size-[50%]" />
      )}
    </span>
  );
}

export const DRAWN_CROPS = Object.keys(GLYPHS);

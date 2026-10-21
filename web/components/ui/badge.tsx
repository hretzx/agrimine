import type { ComponentProps } from "react";
import { cn } from "@/lib/cn";

export type Tone = "mint" | "butter" | "coral" | "lavender" | "sky" | "ink" | "neutral";

// tint background + readable ink of the same hue (the -ink tokens switch with the theme)
const TONES: Record<Tone, string> = {
  mint: "bg-mint/18 text-mint-ink",
  butter: "bg-butter/28 text-butter-ink",
  coral: "bg-coral/18 text-coral-ink",
  lavender: "bg-lavender/24 text-lavender-ink",
  sky: "bg-sky/20 text-sky-ink",
  ink: "bg-nav-on text-nav-on-ink",
  neutral: "bg-inset text-ink-2 shadow-[inset_0_0_0_1px_var(--line)]",
};

/** Small status pill. Colour is never the only signal: always put words in it. */
export function Badge({ tone = "neutral", className, ...props }: ComponentProps<"span"> & { tone?: Tone }) {
  return (
    <span
      className={cn("inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-[0.2rem] text-[0.72rem] font-semibold [&>svg]:size-3", TONES[tone], className)}
      {...props}
    />
  );
}

/** The three soil-health words used everywhere: good, moderate, needs attention. */
export const STATUS_TONE = { good: "mint", moderate: "butter", attention: "coral" } as const satisfies Record<string, Tone>;

"use client";

import { Progress } from "@base-ui/react/progress";
import { cn } from "@/lib/cn";

/**
 * A horizontal bar for a 0-100 value (match score, accuracy, soil level). Built on Base UI's Progress, so it exposes
 * role="progressbar" with aria-valuenow. `hatch` draws the diagonal-line empty part. `color` is any CSS colour or gradient.
 */
export function Track({
  value,
  label,
  color = "var(--mint)",
  hatch = false,
  className,
}: {
  value: number;
  label: string;
  color?: string;
  hatch?: boolean;
  className?: string;
}) {
  // two decimals: a tiny value such as 1.8e-8 would otherwise reach aria-valuenow in exponent form, which is not a valid number
  const clamped = Math.round(Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0)) * 100) / 100;
  return (
    <Progress.Root value={clamped} aria-label={label} className={cn("w-full", className)}>
      <Progress.Track
        className={cn(
          "relative h-2 overflow-hidden rounded-full",
          hatch ? "bg-card shadow-[inset_0_0_0_1px_var(--line)] before:absolute before:inset-0 before:bg-[image:var(--hatch)]" : "bg-track",
        )}
      >
        <Progress.Indicator className="relative z-[1] h-full rounded-full transition-[width] duration-500" style={{ background: color }} />
      </Progress.Track>
    </Progress.Root>
  );
}

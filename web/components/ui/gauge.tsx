import { cn } from "@/lib/cn";

type Status = "good" | "moderate" | "attention";
const DOT: Record<Status, string> = { good: "var(--mint)", moderate: "var(--butter)", attention: "var(--coral)" };

/**
 * One reading against a crop's usual range. The track is the whole allowed range of the measurement; the outlined band is
 * where this crop usually grows (10th to 90th percentile); the dot is the reading, coloured by its status.
 * `min`/`max` are the track ends, `low`/`high` the band, `value` the reading (all in the measurement's own units).
 */
export function Gauge({ value, low, high, min, max, status, label }: { value: number; low: number; high: number; min: number; max: number; status: Status; label: string }) {
  const span = max - min || 1;
  const pct = (v: number) => Math.max(0, Math.min(100, ((v - min) / span) * 100));
  return (
    <div role="img" aria-label={label} className="relative h-2 rounded-full bg-track">
      <i className="absolute -inset-y-[0.2rem] rounded-[0.45rem] bg-mint/22 shadow-[inset_0_0_0_1.5px_color-mix(in_srgb,var(--mint)_65%,transparent)]" style={{ left: `${pct(low)}%`, width: `${Math.max(1, pct(high) - pct(low))}%` }} />
      <i className={cn("absolute top-1/2 size-[0.95rem] -translate-x-1/2 -translate-y-1/2 rounded-full shadow-[0_0_0_3px_var(--card),0_2px_6px_rgb(0_0_0/.3)]")} style={{ left: `${pct(value)}%`, background: DOT[status] }} />
    </div>
  );
}

import { EASE_OUT, motion, useCalm } from "@/components/motion";
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
  const calm = useCalm();
  const ease = calm ? { duration: 0 } : { duration: 0.8, ease: EASE_OUT };
  return (
    <div role="img" aria-label={label} className="relative h-2 rounded-full bg-track">
      <motion.i className="absolute -inset-y-[0.2rem] rounded-[0.45rem] bg-mint/22 shadow-[inset_0_0_0_1.5px_color-mix(in_srgb,var(--mint)_65%,transparent)]" initial={calm ? false : { opacity: 0, scaleX: 0.6 }} animate={{ opacity: 1, scaleX: 1, left: `${pct(low)}%`, width: `${Math.max(1, pct(high) - pct(low))}%` }} transition={ease} style={{ originX: 0.5 }} />
      {/* the dot slides to the reading (its centring is a margin, not a transform, so Motion can own the transform) */}
      <motion.i className={cn("absolute top-1/2 -ml-[0.475rem] -mt-[0.475rem] size-[0.95rem] rounded-full shadow-[0_0_0_3px_var(--card),0_2px_6px_rgb(0_0_0/.3)]")} initial={calm ? false : { left: "0%" }} animate={{ left: `${pct(value)}%` }} transition={ease} style={{ background: DOT[status] }} />
    </div>
  );
}

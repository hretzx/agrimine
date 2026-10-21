/** Small pure helpers for the hand-drawn SVG charts (so they can be unit-tested without a browser). */

/** A straight-line scale: domain [d0, d1] -> range [r0, r1]. */
export function linear([d0, d1]: [number, number], [r0, r1]: [number, number]) {
  const span = d1 - d0 || 1;
  return (v: number) => r0 + ((v - d0) / span) * (r1 - r0);
}

/** About `count` round tick values covering [min, max]: 20, 25, 30 rather than 19.7, 24.3 ... */
export function niceTicks(min: number, max: number, count = 4): number[] {
  const raw = (max - min) / Math.max(1, count);
  const pow = 10 ** Math.floor(Math.log10(raw || 1));
  const step = [1, 2, 5, 10].map((m) => m * pow).find((s) => s >= raw) ?? pow * 10;
  const ticks: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) ticks.push(Number(v.toFixed(6)));
  return ticks;
}

export type LabelItem = { x: number; y: number; r: number; text: string };
export type PlacedLabel = { index: number; x: number; y: number; anchor: "start" | "end" };

/**
 * Put a text label beside each bubble without covering another label or another bubble's centre. Bubbles are tried in the
 * order given (put the ones that matter most first); a label that fits nowhere is left out (its bubble still has a tooltip).
 * Text width is estimated from the character count, so it also works for Marathi.
 */
export function placeLabels(items: LabelItem[], width: number, height: number, charWidth = 5.6, lineHeight = 10): PlacedLabel[] {
  const placed: { x0: number; x1: number; y0: number; y1: number }[] = [];
  const out: PlacedLabel[] = [];
  const overlaps = (a: (typeof placed)[number], b: (typeof placed)[number]) => a.x0 < b.x1 && a.x1 > b.x0 && a.y0 < b.y1 && a.y1 > b.y0;
  items.forEach((it, index) => {
    const w = it.text.length * charWidth + 2;
    for (const anchor of ["start", "end"] as const) {
      const x = anchor === "start" ? it.x + it.r + 3 : it.x - it.r - 3;
      const box = { x0: anchor === "start" ? x : x - w, x1: anchor === "start" ? x + w : x, y0: it.y - lineHeight / 2, y1: it.y + lineHeight / 2 };
      const inside = box.x0 >= 0 && box.x1 <= width && box.y0 >= 0 && box.y1 <= height;
      const hitsLabel = placed.some((p) => overlaps(p, box));
      const hitsBubble = items.some((o, j) => j !== index && o.x > box.x0 - o.r * 0.4 && o.x < box.x1 + o.r * 0.4 && o.y > box.y0 - o.r * 0.4 && o.y < box.y1 + o.r * 0.4);
      if (inside && !hitsLabel && !hitsBubble) {
        placed.push(box);
        out.push({ index, x, y: it.y + 3.3, anchor });
        return;
      }
    }
  });
  return out;
}

/** Colour token for the k-th K-Means group (cycles after 5). */
// up to ten groups (the teacher page lets k go to 10); the first five are the theme colours used on Home
export const CLUSTER_COLORS = ["var(--mint)", "var(--sky)", "var(--butter)", "var(--lavender)", "var(--coral)", "#2f9e9a", "#d96aa7", "#8a6d3b", "#5b6ee1", "#9aa33a"];
export const clusterColor = (k: number) => CLUSTER_COLORS[k % CLUSTER_COLORS.length];

/** Colour token per crop family (the family name comes from the API). */
export const FAMILY_COLORS: Record<string, string> = {
  Cereals: "var(--mint)",
  Pulses: "var(--sky)",
  Fruits: "var(--butter)",
  "Fibre & cash crops": "var(--lavender)",
};
export const familyColor = (family: string) => FAMILY_COLORS[family] ?? "var(--ink-3)";

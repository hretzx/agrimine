import { describe, expect, it } from "vitest";
import { clusterColor, familyColor, linear, niceTicks, placeLabels } from "@/lib/charts";
import { greetingKey, readingText, cropName, familyName, axisTitle } from "@/lib/labels";
import { patternItem, shortDate } from "@/components/home/format";
import { LAB_PAGE, labLink } from "@/lib/lab";

describe("linear scale", () => {
  it("maps the ends and the middle", () => {
    const s = linear([10, 30], [0, 200]);
    expect([s(10), s(20), s(30)]).toEqual([0, 100, 200]);
  });
  it("can flip (a y axis grows upward)", () => {
    expect(linear([0, 100], [180, 20])(100)).toBe(20);
  });
  it("does not divide by zero for a flat domain", () => {
    expect(Number.isFinite(linear([5, 5], [0, 100])(5))).toBe(true);
  });
});

describe("niceTicks", () => {
  it("returns round numbers inside the range", () => {
    expect(niceTicks(19.7, 34.3, 4)).toEqual([20, 25, 30]);
    expect(niceTicks(0, 260, 3)).toEqual([0, 100, 200]);
  });
  it("always has at least one tick for a normal range", () => {
    expect(niceTicks(3.1, 3.4, 4).length).toBeGreaterThan(0);
  });
});

describe("placeLabels", () => {
  const W = 330, H = 214;
  const box = (l: { x: number; y: number; anchor: string }, text: string) => {
    const w = text.length * 5.6;
    return { x0: l.anchor === "start" ? l.x : l.x - w, x1: l.anchor === "start" ? l.x + w : l.x, y0: l.y - 8, y1: l.y + 2 };
  };
  it("puts a lone label beside its bubble, to the right when there is room", () => {
    const [l] = placeLabels([{ x: 100, y: 100, r: 8, text: "Rice" }], W, H);
    expect(l.anchor).toBe("start");
    expect(l.x).toBeGreaterThan(108);
  });
  it("moves a label to the left when the right side would leave the chart", () => {
    const [l] = placeLabels([{ x: 320, y: 100, r: 8, text: "Papaya" }], W, H);
    expect(l.anchor).toBe("end");
  });
  it("never lets two labels overlap, even when no bubble centre is in the way", () => {
    // Found by search: with only the bubble rule, "Rice" and "Coffee" were both placed to the right and printed on top of
    // each other. Only the label-versus-label rule prevents that.
    const items = [{ x: 186, y: 73, r: 6, text: "Rice" }, { x: 179, y: 72, r: 8, text: "Coffee" }];
    const out = placeLabels(items, W, H);
    expect(out.length).toBeGreaterThanOrEqual(1);
    const boxes = out.map((l) => box(l, items[l.index].text));
    for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {
      const a = boxes[i], b = boxes[j];
      expect(a.x0 < b.x1 && a.x1 > b.x0 && a.y0 < b.y1 && a.y1 > b.y0, `label ${i} overlaps label ${j}`).toBe(false);
    }
  });
  it("leaves a label out rather than overlapping, and keeps every placed label inside the chart", () => {
    const items = Array.from({ length: 12 }, (_, i) => ({ x: 150 + (i % 3) * 3, y: 100 + i, r: 9, text: `Crop${i}` }));
    const out = placeLabels(items, W, H);
    expect(out.length).toBeLessThan(items.length);
    for (const l of out) {
      const b = box(l, items[l.index].text);
      expect(b.x0).toBeGreaterThanOrEqual(0);
      expect(b.x1).toBeLessThanOrEqual(W);
    }
  });
  it("sizes Marathi text by character count too", () => {
    expect(placeLabels([{ x: 100, y: 100, r: 8, text: "तंतू व नगदी पिके" }], W, H)).toHaveLength(1);
  });
});

describe("colours", () => {
  it("cycles group colours and has a fallback for an unknown family", () => {
    expect(new Set(Array.from({ length: 10 }, (_, k) => clusterColor(k))).size).toBe(10);   // up to ten groups, all told apart
    expect(clusterColor(0)).toBe(clusterColor(10));                                          // and it cycles after that
    expect(familyColor("Cereals")).not.toBe(familyColor("Pulses"));
    expect(familyColor("Unknown")).toBe("var(--ink-3)");
  });
});

describe("labels", () => {
  it("picks the greeting by hour", () => {
    expect([greetingKey(6), greetingKey(11), greetingKey(12), greetingKey(16), greetingKey(17), greetingKey(23)]).toEqual([
      "home.greeting.morning", "home.greeting.morning", "home.greeting.afternoon", "home.greeting.afternoon", "home.greeting.evening", "home.greeting.evening"]);
  });
  it("formats readings with the registry unit, none for N, P, K", () => {
    expect(readingText(20.94, { key: "temperature", unit: "°C" })).toBe("20.9 °C");
    expect(readingText(202.9, { key: "rainfall", unit: "mm" })).toBe("203 mm");
    expect(readingText(90, { key: "N", unit: "" })).toBe("90");
    expect(readingText(6.5, { key: "ph", unit: "" })).toBe("6.5");
  });
  it("names crops, families and axes in the chosen language", () => {
    const rice = { label: "Rice", label_mr: "भात" };
    expect([cropName(rice, "en"), cropName(rice, "mr")]).toEqual(["Rice", "भात"]);
    expect(familyName([{ key: "Pulses", label: "Pulses", label_mr: "कडधान्ये" }], "Pulses", "mr")).toBe("कडधान्ये");
    const features = [{ key: "rainfall", label: "Rainfall", label_mr: "पाऊस", name: "Rainfall", unit: "mm", lo: 20, hi: 300, default: 94.9 }];
    expect([axisTitle(features, "rainfall", "en"), axisTitle(features, "rainfall", "mr")]).toEqual(["Rainfall (mm)", "पाऊस (mm)"]);
  });
});

describe("pattern and date formatting", () => {
  const meta = {
    crops: [{ key: "chickpea", label: "Chickpea", label_mr: "हरभरा", family: "Pulses" }],
    features: [{ key: "K", label: "Potassium (K)", label_mr: "पालाश (K)", name: "K", unit: "", lo: 5, hi: 205, default: 32 }],
  } as never;
  const word = (w: string) => ({ high: "जास्त", low: "कमी" })[w] ?? w;
  it("turns rule items into words in either language", () => {
    expect(patternItem("K=high", meta, "en", (w) => w)).toBe("Potassium high");
    expect(patternItem("K=high", meta, "mr", word as never)).toBe("पालाश जास्त");
    expect(patternItem("crop=chickpea", meta, "mr", word as never)).toBe("हरभरा");
  });
  it("shows a saved timestamp as a short date, and survives a bad one", () => {
    expect(shortDate("2026-10-20 13:05", "en")).toBe("20 Oct");
    expect(shortDate("garbage", "en")).toBe("garbage");
  });
  it("keeps Latin digits in Marathi (the rest of the Marathi text uses them) but uses the Marathi month name", () => {
    const d = shortDate("2026-10-14 21:48", "mr");
    expect(d).not.toMatch(/[\u0966-\u096F]/);
    expect(d).toMatch(/^14 /);
    expect(d).toMatch(/[\u0900-\u097F]/);
  });
});

describe("lab links", () => {
  it("opens a lab page on the same check, or the lab home, and leaves the check out when there is none", () => {
    expect(labLink("http://localhost:8501", "crop-advisor", 4)).toBe("http://localhost:8501/crop-advisor?check=4");
    expect(labLink("http://localhost:8501/", undefined, 4)).toBe("http://localhost:8501?check=4");   // no double slash
    expect(labLink("http://192.168.1.20:8501", "water-lab")).toBe("http://192.168.1.20:8501/water-lab");
  });
  it("has no profile-match page (there is none in the lab)", () => {
    expect(Object.keys(LAB_PAGE)).not.toContain("match");
  });
});

"use client";

import { useEffect, useMemo, useState } from "react";
import type { CheckOut, FeatureInfo, Readings } from "@/lib/api/client";
import { useCurrentCheck, useMeta } from "@/lib/data";
import { parseReadings, startingValues } from "@/lib/readings";

/** Wait until a value has stopped changing for `ms` before using it (so typing "202" does not ask the API about "2" and "20"). */
export function useDebounced<T>(value: T, ms = 300): T {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setSettled(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return settled;
}

export type ReadingsState = {
  features: FeatureInfo[];
  /** The text in each box. */
  text: Record<string, string>;
  setText: (key: string, value: string) => void;
  /** All seven readings as numbers, once every box is valid and typing has paused. Pages ask the API only with this. */
  readings?: Readings;
  /** True while every box is valid but the pause has not elapsed. */
  settling: boolean;
  /** True when every box is valid (the result on screen belongs to what is typed). */
  valid: boolean;
  edited: boolean;
  reset: () => void;
  check?: CheckOut;
  ready: boolean;
  error?: Error;
};

/**
 * The readings a page works with: the current check's values (or the dataset's typical values when nothing is saved), which the
 * visitor can edit to try things out. Editing never saves anything.
 */
export function useReadings(): ReadingsState {
  const meta = useMeta();
  const { check, loading, error } = useCurrentCheck();
  const features = useMemo(() => meta.data?.features ?? [], [meta.data]);
  const start = useMemo(() => startingValues(features, check?.values), [features, check]);
  const startKey = JSON.stringify(start);
  const [edits, setEdits] = useState<{ base: string; text: Record<string, string> }>({ base: "", text: {} });
  const text = edits.base === startKey ? { ...start, ...edits.text } : start; // a different check starts fresh
  const parsed = parseReadings(features, text);
  const parsedKey = parsed ? JSON.stringify(parsed) : "";
  const debouncedKey = useDebounced(parsedKey, 300);
  const settledKey = debouncedKey || parsedKey; // the first valid values count at once; only later edits wait for a pause
  const readings = useMemo(() => (settledKey ? (JSON.parse(settledKey) as Readings) : undefined), [settledKey]);
  return {
    features,
    text,
    setText: (key, value) => setEdits((e) => ({ base: startKey, text: { ...(e.base === startKey ? e.text : {}), [key]: value } })),
    readings: parsed ? readings : undefined,
    settling: !!parsed && parsedKey !== settledKey,
    valid: !!parsed,
    edited: Object.keys(text).some((k) => text[k] !== start[k]),
    reset: () => setEdits({ base: startKey, text: {} }),
    check,
    ready: !!meta.data && !loading,
    error: (meta.error ?? error) as Error | undefined,
  };
}

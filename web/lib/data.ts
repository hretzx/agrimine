"use client";

import { useSearchParams } from "next/navigation";
import useSWR from "swr";
import { api, type AprioriQuery, type CheckOut, type Readings } from "@/lib/api/client";

// Everything on screen comes from the API through these hooks. Data never changes while a page is open, except when a check
// is saved (which navigates), so nothing is re-fetched on focus.
const OPTIONS = { revalidateOnFocus: false, shouldRetryOnError: false } as const;

/** Is the technical lab up, and where? Asked again every few seconds while it is not (it takes a few seconds to start). */
export const useLab = () => useSWR("lab", api.lab, { ...OPTIONS, refreshInterval: (d) => (d?.available ? 0 : 3000) });
export const useMeta = () => useSWR("meta", api.meta, OPTIONS);
export const useRecentChecks = (limit = 6) => useSWR(["checks", limit], () => api.recentChecks(limit), OPTIONS);
export const useRecommendation = (values?: Readings) => useSWR(values ? ["recommend", JSON.stringify(values)] : null, () => api.recommend(values!), OPTIONS);
export const useDoctor = (values?: Readings, crop?: string) => useSWR(values && crop ? ["doctor", JSON.stringify(values), crop] : null, () => api.doctor(values!, crop!), OPTIONS);
/** Crop Doctor reports for several crops at once (the compare tables). Keys are sorted so the same set is one cache entry. */
export const useDoctors = (values: Readings | undefined, crops: string[]) =>
  useSWR(values && crops.length ? ["doctors", JSON.stringify(values), [...crops].sort().join(",")] : null, () => Promise.all(crops.map((c) => api.doctor(values!, c))), OPTIONS);
export const usePlanB = (values?: Readings, preferred?: string) => useSWR(values && preferred ? ["planb", JSON.stringify(values), preferred] : null, () => api.planB(values!, preferred!), OPTIONS);
/** The ID3 teacher page: the tree's answer and the path it took for these readings. */
export const useId3 = (values?: Readings) => useSWR(values ? ["id3", JSON.stringify(values)] : null, () => api.id3(values!), OPTIONS);
/** The Naive Bayes teacher page (the lab's Model Council): both classifiers on these readings. */
export const useNaiveBayes = (values?: Readings) => useSWR(values ? ["nb", JSON.stringify(values)] : null, () => api.naiveBayes(values!), OPTIONS);
/** The K-Means teacher page (the lab's Cluster Explorer): k groups on a PCA map, for these readings. */
export const useKMeans = (values: Readings | undefined, k: number) => useSWR(values ? ["kmeans", JSON.stringify(values), k] : null, () => api.kmeans(values!, k), OPTIONS);
/** The Apriori teacher page (the lab's Pattern Mining): the rules at these settings. Needs no readings. */
export const useApriori = (q: AprioriQuery) => useSWR(["apriori", q.minSupport, q.minConfidence, q.maxLen, q.crop, q.onlyCrop], () => api.apriori(q), OPTIONS);
/** The Hierarchical teacher page: the family tree of the 22 crops. Needs no readings. */
export const useHierarchical = (method: string, k: number) => useSWR(["hier", method, k], () => api.hierarchical(method, k), OPTIONS);
export const useFarms = (k: number, check?: number) => useSWR(["farms", k, check ?? 0], () => api.farms(k, check), OPTIONS);
export const useNeeds = () => useSWR("needs", api.needs, OPTIONS);
export const useGain = () => useSWR("gain", api.gain, OPTIONS);
export const usePatterns = (limit = 3) => useSWR(["patterns", limit], () => api.patterns(limit), OPTIONS);
export const useAccuracy = () => useSWR("accuracy", api.accuracy, OPTIONS);

export type CurrentCheck = {
  /** The check the page is about: the one named in ?check=, else the most recent one, else undefined (nothing saved yet). */
  check?: CheckOut;
  /** True while the first answer has not arrived. */
  loading: boolean;
  /** True when nothing has ever been saved. */
  empty: boolean;
  error?: Error;
  /** The id from the address bar, if any (links keep it so the page you move to is about the same check). */
  explicitId?: number;
};

export function useCurrentCheck(): CurrentCheck {
  const raw = useSearchParams().get("check");
  const explicitId = raw && /^\d+$/.test(raw) ? Number(raw) : undefined;
  const one = useSWR(explicitId ? ["check", explicitId] : null, () => api.check(explicitId!), OPTIONS);
  const latest = useSWR(explicitId ? null : ["checks", 1], () => api.recentChecks(1), OPTIONS);
  if (explicitId) return { check: one.data, loading: one.isLoading, empty: false, error: one.error, explicitId };
  return { check: latest.data?.[0], loading: latest.isLoading, empty: !latest.isLoading && !latest.error && latest.data?.length === 0, error: latest.error };
}

/** "/en/doctor/" + the check id, when the address bar names one: `withCheck("/en/doctor/", 18)` -> "/en/doctor/?check=18". */
export const withCheck = (path: string, id?: number) => (id ? `${path}?check=${id}` : path);

/**
 * Typed access to the AgriMine API. Types come from api/openapi.json (npm run gen:api), so a field renamed in Python is a
 * TypeScript error here, never a silent undefined in the browser.
 */
import type { components } from "./schema";

export type Schemas = components["schemas"];
export type Readings = Schemas["Readings"];
export type Recommendation = Schemas["Recommendation"];
export type CheckOut = Schemas["CheckOut"];
export type DoctorResponse = Schemas["DoctorResponse"];
export type PlanBResponse = Schemas["PlanBResponse"];
export type Meta = Schemas["Meta"];
export type CropRef = Schemas["CropRef"];
export type ErrorBody = Schemas["ErrorBody"];
export type FarmsResponse = Schemas["FarmsResponse"];
export type CropNeeds = Schemas["CropNeeds"];
export type GainRow = Schemas["GainRow"];
export type Pattern = Schemas["Pattern"];
export type PatternsResponse = Schemas["PatternsResponse"];
export type AccuracyResponse = Schemas["AccuracyResponse"];
export type FeatureInfo = Schemas["FeatureInfo"];
export type LabStatus = Schemas["LabStatus"];
export type ID3Report = Schemas["ID3Report"];
export type NBReport = Schemas["NBReport"];
export type KMeansReport = Schemas["KMeansReport"];
export type AprioriReport = Schemas["AprioriReport"];
export type HierarchicalReport = Schemas["HierarchicalReport"];

/** Where the API lives: the same origin in production (FastAPI serves this site); NEXT_PUBLIC_API_URL in development. */
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

/** An API error in the API's one error shape. */
export class ApiError extends Error {
  constructor(public status: number, public body: ErrorBody) {
    super(body.message);
  }
  /** Messages per field, for showing next to the inputs. */
  get fields(): Record<string, string> {
    return Object.fromEntries((this.body.errors ?? []).filter((e) => e.field).map((e) => [e.field as string, e.message as string]));
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}/api${path}`, { headers: { "content-type": "application/json" }, ...init });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, body ?? { code: "network", message: res.statusText, field: null, errors: null });
  return body as T;
}

/** The settings of the Pattern Mining page. */
export type AprioriQuery = { minSupport: number; minConfidence: number; maxLen: number; crop: string; onlyCrop: boolean };

const post = <T>(path: string, data: unknown) => request<T>(path, { method: "POST", body: JSON.stringify(data) });

export const api = {
  meta: () => request<Meta>("/meta"),
  recommend: (values: Readings) => post<Recommendation>("/recommend", values),
  createCheck: (values: Readings) => post<CheckOut>("/checks", values),
  check: (id: number) => request<CheckOut>(`/checks/${id}`),
  recentChecks: (limit = 10) => request<CheckOut[]>(`/checks?limit=${limit}`),
  doctor: (values: Readings, crop: string) => post<DoctorResponse>("/doctor", { values, crop }),
  planB: (values: Readings, preferred: string) => post<PlanBResponse>("/plan-b", { values, preferred }),
  farms: (k: number, check?: number) => request<FarmsResponse>(`/insights/farms?k=${k}${check ? `&check=${check}` : ""}`),
  needs: () => request<CropNeeds[]>("/insights/needs"),
  gain: () => request<GainRow[]>("/insights/gain"),
  patterns: (limit = 5) => request<PatternsResponse>(`/insights/patterns?limit=${limit}`),
  accuracy: () => request<AccuracyResponse>("/insights/accuracy"),
  lab: () => request<LabStatus>("/lab"),
  id3: (values: Readings) => post<ID3Report>("/teachers/id3", values),
  naiveBayes: (values: Readings) => post<NBReport>("/teachers/naive-bayes", values),
  apriori: (q: AprioriQuery) => request<AprioriReport>(`/teachers/apriori?${new URLSearchParams({ min_support: String(q.minSupport), min_confidence: String(q.minConfidence), max_len: String(q.maxLen), only_crop: String(q.onlyCrop), ...(q.crop ? { crop: q.crop } : {}) })}`),
  hierarchical: (method: string, k: number) => request<HierarchicalReport>(`/teachers/hierarchical?method=${method}&k=${k}`),
  kmeans: (values: Readings, k: number) => post<KMeansReport>(`/teachers/kmeans?k=${k}`, values),
};

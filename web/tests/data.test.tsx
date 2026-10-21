import { renderHook, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

let search = "";
vi.mock("next/navigation", () => ({ useSearchParams: () => new URLSearchParams(search) }));

import { useCurrentCheck, withCheck } from "@/lib/data";

const wrapper = ({ children }: { children: ReactNode }) => <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>{children}</SWRConfig>;
const json = (body: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } }));
const check = (id: number) => ({ id, values: {}, status: "predicted" });

afterEach(() => { vi.restoreAllMocks(); search = ""; });

describe("withCheck", () => {
  it("adds ?check= only when an id is known", () => {
    expect(withCheck("/en/doctor/", 18)).toBe("/en/doctor/?check=18");
    expect(withCheck("/en/doctor/")).toBe("/en/doctor/");
  });
});

describe("useCurrentCheck", () => {
  it("uses the check named in the address bar", async () => {
    search = "check=7";
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((url) => json(String(url).endsWith("/checks/7") ? check(7) : []));
    const { result } = renderHook(() => useCurrentCheck(), { wrapper });
    await waitFor(() => expect(result.current.check?.id).toBe(7));
    expect(result.current.explicitId).toBe(7);
    expect(fetchMock.mock.calls.some(([u]) => String(u).includes("/checks?limit"))).toBe(false); // it did not ask for "the latest"
  });
  it("falls back to the newest saved check", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => json([check(9)]));
    const { result } = renderHook(() => useCurrentCheck(), { wrapper });
    await waitFor(() => expect(result.current.check?.id).toBe(9));
    expect(result.current.explicitId).toBeUndefined();
    expect(result.current.empty).toBe(false);
  });
  it("says 'empty' (not 'loading forever') when nothing was ever saved", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => json([]));
    const { result } = renderHook(() => useCurrentCheck(), { wrapper });
    await waitFor(() => expect(result.current.empty).toBe(true));
    expect(result.current.check).toBeUndefined();
    expect(result.current.loading).toBe(false);
  });
  it("ignores a garbage ?check= value instead of requesting /checks/NaN", async () => {
    search = "check=abc";
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(() => json([check(3)]));
    const { result } = renderHook(() => useCurrentCheck(), { wrapper });
    await waitFor(() => expect(result.current.check?.id).toBe(3));
    expect(fetchMock.mock.calls.every(([u]) => !String(u).includes("NaN") && !String(u).includes("abc"))).toBe(true);
  });
  it.each(["-5", "7.5", "1e3", "0x10", ""])("never requests a check for the odd value ?check=%s", async (odd) => {
    search = `check=${odd}`;
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(() => json([check(3)]));
    const { result } = renderHook(() => useCurrentCheck(), { wrapper });
    await waitFor(() => expect(result.current.check?.id).toBe(3));       // it fell back to the newest check
    expect(fetchMock.mock.calls.every(([u]) => /\/checks\?limit=1$/.test(String(u)))).toBe(true);
  });
  it("reports an unknown check id as an error", async () => {
    search = "check=999";
    vi.spyOn(globalThis, "fetch").mockImplementation(() => json({ code: "unknown_check", message: "no", field: "check_id", errors: null }, 404));
    const { result } = renderHook(() => useCurrentCheck(), { wrapper });
    await waitFor(() => expect(result.current.error).toBeDefined());
    expect(result.current.check).toBeUndefined();
  });
});

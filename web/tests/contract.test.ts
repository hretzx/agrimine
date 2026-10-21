// @vitest-environment node
import openapiTS, { astToString } from "openapi-typescript";
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const strip = (s: string) => s.replace(/^\/\*\*[\s\S]*?\*\/\s*/, "").replace(/\s+$/g, "");

describe("API contract", () => {
  it("lib/api/schema.d.ts is exactly what api/openapi.json generates (run: npm run gen:api)", async () => {
    const generated = astToString(await openapiTS(new URL("../../api/openapi.json", import.meta.url)));
    const committed = readFileSync(new URL("../lib/api/schema.d.ts", import.meta.url), "utf8");
    expect(strip(committed)).toBe(strip(generated));
  });
  it("declares the one error shape", () => {
    const committed = readFileSync(new URL("../lib/api/schema.d.ts", import.meta.url), "utf8");
    expect(committed).toContain("ErrorBody");
  });
});

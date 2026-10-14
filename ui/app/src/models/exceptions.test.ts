import { describe, expect, it } from "vitest";
import { isRetryableApiError } from "./exceptions";

describe("isRetryableApiError", () => {
  it.each([408, 429, 500, 503])("returns true for status %s", (status) => {
    expect(isRetryableApiError({ status })).toBe(true);
  });

  it.each([undefined, 400, 403, null, "503"])("returns false for status %s", (status) => {
    expect(isRetryableApiError({ status })).toBe(false);
  });

  it("returns false for values without an API status", () => {
    expect(isRetryableApiError(null)).toBe(false);
    expect(isRetryableApiError("unavailable")).toBe(false);
  });
});

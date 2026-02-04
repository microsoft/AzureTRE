import { describe, it, expect } from "vitest";
import { LoadingState } from "./loadingState";

describe("LoadingState", () => {
  it("should have correct enum values", () => {
    expect(LoadingState.Loading).toBe("loading");
    expect(LoadingState.Ok).toBe("ok");
    expect(LoadingState.Error).toBe("error");
    expect(LoadingState.AccessDenied).toBe("access-denied");
    expect(LoadingState.NotSupported).toBe("not-supported");
  });
});

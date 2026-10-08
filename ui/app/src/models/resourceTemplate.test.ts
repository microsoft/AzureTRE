import { describe, expect, it } from "vitest";
import { getActionDisplayName } from "./resourceTemplate";

describe("getActionDisplayName", () => {
  it.each([
    ["start", "Start"],
    ["reset_password", "Reset password"],
    ["rotate-keys", "Rotate keys"],
  ])("formats %s as %s", (name, expected) => {
    expect(getActionDisplayName(name)).toBe(expected);
  });
});

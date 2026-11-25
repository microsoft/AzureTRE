import { describe, expect, it } from "vitest";
import { getListApiScope } from "./ResourceDetailsLayout";

describe("getListApiScope", () => {
  const ownerOrAdmin = ["TREAdmin", "WorkspaceOwner"];

  it("uses the workspace scope when a workspace role grants access", () => {
    expect(getListApiScope(["WorkspaceOwner"], "ws-scope", ownerOrAdmin)).toBe("ws-scope");
  });

  it("uses the core scope for a TRE Admin whose workspace role does not grant access", () => {
    expect(getListApiScope(["WorkspaceResearcher"], "ws-scope", ownerOrAdmin)).toBe("");
  });

  it("uses the core scope when there is no workspace role", () => {
    expect(getListApiScope([], "ws-scope", ownerOrAdmin)).toBe("");
  });

  it("keeps the previous behaviour when no allowed roles are given", () => {
    expect(getListApiScope(["WorkspaceResearcher"], "ws-scope")).toBe("ws-scope");
    expect(getListApiScope([], "ws-scope")).toBe("");
  });
});

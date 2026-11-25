import { describe, expect, it } from "vitest";
import { isOwnedByUser } from "./userResource";
import { UserResource } from "./userResource";

const resource = (ownerId?: string, properties: Record<string, unknown> = {}) =>
  ({
    ownerId,
    properties,
  }) as UserResource;

describe("isOwnedByUser", () => {
  it("matches the ownerId field", () => {
    expect(isOwnedByUser(resource("user-id"), "user-id")).toBe(true);
  });

  it("matches either supported owner property name", () => {
    expect(isOwnedByUser(resource(undefined, { owner_id: "user-id" }), "user-id")).toBe(true);
    expect(isOwnedByUser(resource(undefined, { ownerId: "user-id" }), "user-id")).toBe(true);
  });

  it("does not match missing or different owner IDs", () => {
    expect(isOwnedByUser(resource("another-user"), "user-id")).toBe(false);
    expect(isOwnedByUser(resource("user-id"), "")).toBe(false);
  });

  it("ignores owner properties when ownerId is set", () => {
    expect(isOwnedByUser(resource("another-user", { owner_id: "user-id" }), "user-id")).toBe(false);
  });
});

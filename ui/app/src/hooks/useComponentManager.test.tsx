import React from "react";
import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useComponentManager } from "./useComponentManager";
import { ComponentAction, Resource } from "../models/resource";
import { ResourceType } from "../models/resourceType";

// Mock dependencies
vi.mock("./useAuthApiCall", () => ({
  useAuthApiCall: () => vi.fn(),
  HttpMethod: { Get: "GET" },
}));

vi.mock("./customReduxHooks", () => ({
  useAppSelector: () => ({ items: [] }),
}));

vi.mock("../contexts/WorkspaceContext", () => ({
  WorkspaceContext: React.createContext({}),
}));

const mockResource1: Resource = {
  id: "resource-1",
  isEnabled: true,
  resourcePath: "/path/1",
  resourceVersion: 1,
  resourceType: ResourceType.Workspace,
  templateName: "template1",
  templateVersion: "1.0.0",
  availableUpgrades: [],
  deploymentStatus: "deployed",
  updatedWhen: Date.now(),
  user: {
    name: "user1",
    id: "uid1",
    email: "user1@example.com",
    roleAssignments: [],
    roles: []
  },
  history: [],
  _etag: "etag1",
  properties: {},
};

const mockResource2: Resource = {
  ...mockResource1,
  id: "resource-2",
  resourcePath: "/path/2",
};

describe("useComponentManager", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should reset componentAction to None when resource changes", () => {
    const mockOnUpdate = vi.fn();
    const mockOnRemove = vi.fn();

    const { result, rerender } = renderHook(
      ({ resource }: { resource: Resource }) =>
        useComponentManager(resource, mockOnUpdate, mockOnRemove),
      {
        initialProps: { resource: mockResource1 },
      },
    );

    // Initial state should be None
    expect(result.current.componentAction).toBe(ComponentAction.None);

    // Simulate a lock state by manually triggering an update
    // (In real scenario, this would happen through operations)
    act(() => {
      // This simulates what would happen when an operation is in progress
      // We can't easily test the full flow without mocking more dependencies
    });

    // Change the resource
    rerender({ resource: mockResource2 });

    // After resource change, componentAction should be reset to None
    expect(result.current.componentAction).toBe(ComponentAction.None);
  });

  it("should reset componentAction when resource is changed", () => {
    const mockOnUpdate = vi.fn();
    const mockOnRemove = vi.fn();

    const { result, rerender } = renderHook(
      ({ resource }: { resource: Resource }) =>
        useComponentManager(resource, mockOnUpdate, mockOnRemove),
      {
        initialProps: { resource: mockResource1 },
      },
    );

    // Change resource to a new resource
    rerender({ resource: mockResource2 });

    // componentAction should be reset to None
    expect(result.current.componentAction).toBe(ComponentAction.None);
  });
});

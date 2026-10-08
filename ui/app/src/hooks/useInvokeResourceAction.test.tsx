import React from "react";
import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { WorkspaceContext } from "../contexts/WorkspaceContext";
import { Resource } from "../models/resource";
import { ResourceType } from "../models/resourceType";
import { useInvokeResourceAction } from "./useInvokeResourceAction";

const mockApiCall = vi.hoisted(() => vi.fn());
vi.mock("./useAuthApiCall", () => ({
  useAuthApiCall: () => mockApiCall,
  HttpMethod: { Post: "POST" },
}));
vi.mock("./customReduxHooks", () => ({ useAppDispatch: () => vi.fn() }));

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <WorkspaceContext.Provider value={{ workspaceApplicationIdURI: "workspace-scope" } as any}>
    {children}
  </WorkspaceContext.Provider>
);

const invoke = async (resourceType: ResourceType) => {
  const { result } = renderHook(() => useInvokeResourceAction(), { wrapper });
  await result.current({ resourceType, resourcePath: "/path" } as Resource, "start");
  return mockApiCall.mock.calls[0][2];
};

describe("useInvokeResourceAction", () => {
  beforeEach(() => mockApiCall.mockReset().mockResolvedValue({}));

  it.each([ResourceType.WorkspaceService, ResourceType.UserResource])("uses the workspace token for %s", async (t) => {
    expect(await invoke(t)).toBe("workspace-scope");
  });

  it.each([ResourceType.Workspace, ResourceType.SharedService])("uses the core TRE token for %s", async (t) => {
    expect(await invoke(t)).toBeUndefined();
  });
});

import React from "react";
import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppRolesContext } from "../contexts/AppRolesContext";
import { WorkspaceContext } from "../contexts/WorkspaceContext";
import { ResourceType } from "../models/resourceType";
import { UserResource } from "../models/userResource";
import { WorkspaceRoleName } from "../models/roleNames";
import { clearResourceTemplateCache, useResourceTemplate } from "./useResourceTemplate";

const { mockApiCall } = vi.hoisted(() => ({ mockApiCall: vi.fn() }));

vi.mock("./useAuthApiCall", () => ({
  useAuthApiCall: () => mockApiCall,
  HttpMethod: { Get: "GET" },
}));

const resource = {
  id: "user-resource",
  resourceType: ResourceType.UserResource,
  templateName: "user-template",
  parentWorkspaceServiceId: "workspace-service",
} as UserResource;

const workspaceContext = {
  workspace: { id: "workspace" },
  workspaceApplicationIdURI: "workspace-scope",
  roles: [WorkspaceRoleName.WorkspaceOwner],
};

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <AppRolesContext.Provider value={{ roles: [], setAppRoles: vi.fn() }}>
    <WorkspaceContext.Provider value={workspaceContext as any}>{children}</WorkspaceContext.Provider>
  </AppRolesContext.Provider>
);

describe("useResourceTemplate", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearResourceTemplateCache();
    mockApiCall.mockImplementation((path: string) =>
      path.includes("workspace-services")
        ? Promise.resolve({ workspaceService: { id: "workspace-service", templateName: "service-template" } })
        : Promise.resolve({ customActions: [] }),
    );
  });

  it("does not return user-resource roles until the parent service is loaded", async () => {
    const { result } = renderHook(() => useResourceTemplate(resource), { wrapper });

    expect(result.current.roles).toEqual([]);

    await waitFor(() => {
      expect(result.current.parentResource.id).toBe("workspace-service");
      expect(result.current.roles).toEqual([
        WorkspaceRoleName.WorkspaceOwner,
        WorkspaceRoleName.WorkspaceResearcher,
        WorkspaceRoleName.AirlockManager,
      ]);
    });
  });

  it("drops the previous resource's template when the resource changes, even if the new fetch fails", async () => {
    mockApiCall.mockImplementation((path: string) => {
      if (path.includes("workspace-services")) {
        return Promise.resolve({ workspaceService: { id: "workspace-service", templateName: "service-template" } });
      }
      return path.endsWith("/user-template")
        ? Promise.resolve({ name: "user-template", customActions: [{ name: "stop", description: "" }] })
        : Promise.reject(new Error("template unavailable"));
    });
    const { result, rerender } = renderHook(({ r }) => useResourceTemplate(r), {
      wrapper,
      initialProps: { r: resource },
    });
    await waitFor(() => expect(result.current.resourceTemplate.customActions).toHaveLength(1));

    rerender({ r: { ...resource, id: "other-resource", templateName: "other-template" } as UserResource });

    expect(result.current.resourceTemplate.customActions).toBeUndefined();
    await waitFor(() => expect(mockApiCall).toHaveBeenCalledWith(expect.stringContaining("other-template"), "GET"));
    expect(result.current.resourceTemplate.customActions).toBeUndefined();
  });
});

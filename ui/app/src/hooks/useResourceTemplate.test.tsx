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

  it("retries a failed template load so actions recover without remounting", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      let templateCalls = 0;
      mockApiCall.mockImplementation((path: string) => {
        if (path.includes("workspace-services")) {
          return Promise.resolve({ workspaceService: { id: "workspace-service", templateName: "service-template" } });
        }
        templateCalls += 1;
        return templateCalls === 1
          ? Promise.reject({ status: 503 })
          : Promise.resolve({ customActions: [{ name: "stop", description: "" }] });
      });
      const { result } = renderHook(() => useResourceTemplate(resource), { wrapper });
      await waitFor(() => expect(templateCalls).toBe(1));
      expect(result.current.resourceTemplate.customActions).toBeUndefined();

      await vi.advanceTimersByTimeAsync(5000);
      await waitFor(() => expect(result.current.resourceTemplate.customActions).toHaveLength(1));
    } finally {
      vi.useRealTimers();
    }
  });

  it("loads actions for the deployed template version and refreshes them after an upgrade", async () => {
    mockApiCall.mockImplementation((path: string) => {
      if (path.includes("workspace-services")) {
        return Promise.resolve({ workspaceService: { id: "workspace-service", templateName: "service-template" } });
      }
      return Promise.resolve({
        customActions: path.endsWith("?version=2.0.0") ? [{ name: "resize", description: "" }] : [],
      });
    });
    const { result, rerender } = renderHook(({ r }) => useResourceTemplate(r), {
      wrapper,
      initialProps: { r: { ...resource, templateVersion: "1.0.0" } as UserResource },
    });
    await waitFor(() =>
      expect(mockApiCall).toHaveBeenCalledWith(expect.stringMatching(/\/user-template\?version=1\.0\.0$/), "GET"),
    );
    await waitFor(() => expect(result.current.resourceTemplate.customActions).toEqual([]));

    rerender({ r: { ...resource, templateVersion: "2.0.0" } as UserResource });
    await waitFor(() => expect(result.current.resourceTemplate.customActions).toHaveLength(1));
  });

  it("does not retry terminal template-load failures", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      let templateCalls = 0;
      mockApiCall.mockImplementation((path: string) => {
        if (path.includes("workspace-services")) {
          return Promise.resolve({ workspaceService: { id: "workspace-service", templateName: "service-template" } });
        }
        templateCalls += 1;
        return Promise.reject({ status: 404 });
      });
      renderHook(() => useResourceTemplate(resource), { wrapper });
      await waitFor(() => expect(templateCalls).toBe(1));

      await vi.advanceTimersByTimeAsync(120000);
      expect(templateCalls).toBe(1);
    } finally {
      vi.useRealTimers();
    }
  });

  it("returns the current workspace as the parent of a workspace service", () => {
    const service = { id: "svc", resourceType: ResourceType.WorkspaceService, templateName: "svc-template" } as any;
    const { result } = renderHook(() => useResourceTemplate(service), { wrapper });
    expect(result.current.parentResource).toBe(workspaceContext.workspace);
  });
});

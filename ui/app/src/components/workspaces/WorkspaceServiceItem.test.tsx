import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { render } from "../../test-utils";
import { WorkspaceServiceItem } from "./WorkspaceServiceItem";
import { WorkspaceService } from "../../models/workspaceService";
import { ResourceType } from "../../models/resourceType";

const mockApiCall = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useParams: () => ({ workspaceServiceId: "test-service" }),
  };
});

vi.mock("../../hooks/useAuthApiCall", () => ({
  useAuthApiCall: () => mockApiCall,
  HttpMethod: { Get: "GET" },
}));

vi.mock("../../hooks/useComponentManager", () => ({
  useComponentManager: () => ({ componentAction: "none", operation: {} }),
}));

vi.mock("../shared/ResourceHeader", () => ({
  ResourceHeader: ({ resource, onRefresh }: any) => (
    <div data-testid="resource-header">
      {resource.id}
      <button onClick={onRefresh}>Refresh</button>
    </div>
  ),
}));

vi.mock("../shared/ResourceBody", () => ({
  ResourceBody: () => <div data-testid="resource-body" />,
}));

vi.mock("../shared/ResourceCardList", () => ({
  ResourceCardList: ({ resources, emptyText }: any) => {
    const React = require("react");
    // Count mounts so tests can check the list isn't unmounted by a refresh.
    React.useEffect(() => {
      (globalThis as any).resourceCardListMounts = ((globalThis as any).resourceCardListMounts || 0) + 1;
    }, []);
    return (
      <div data-testid="resource-card-list">
        {resources.length ? resources.map((resource: any) => resource.id).join(",") : emptyText}
      </div>
    );
  },
}));

const workspaceService = {
  id: "test-service",
  resourceType: ResourceType.WorkspaceService,
  templateName: "test-template",
  templateVersion: "1.0.0",
  resourcePath: "/workspaces/test-workspace/workspace-services/test-service",
  resourceVersion: 1,
  isEnabled: true,
  workspaceId: "test-workspace",
  properties: { display_name: "Test service" },
  _etag: "test-etag",
  updatedWhen: Date.now(),
  deploymentStatus: "deployed",
  availableUpgrades: [],
  history: [],
  user: {
    id: "test-user",
    name: "Test User",
    email: "test@example.com",
    roleAssignments: [],
    roles: [],
  },
} as WorkspaceService;

// Switch the owner's view from the default "My resources" to "All resources".
const showAllResources = async () => {
  fireEvent.click(screen.getByLabelText(/Showing my resources/));
  fireEvent.click(await screen.findByRole("menuitemcheckbox", { name: "All resources", hidden: true }));
};

describe("WorkspaceServiceItem", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("keeps workspace resources visible when the optional workspace users lookup fails", async () => {
    mockApiCall.mockImplementation((endpoint: string) => {
      if (endpoint.endsWith("/workspace-services/test-service")) {
        return Promise.resolve({ workspaceService });
      }
      if (endpoint.endsWith("/user-resources")) {
        return Promise.resolve({ userResources: [{ id: "test-user-resource" }] });
      }
      if (endpoint.endsWith("/user-resource-templates")) {
        return Promise.resolve({ templates: [{}] });
      }
      if (endpoint.endsWith("/users")) {
        return Promise.reject(new Error("Users unavailable"));
      }
      return Promise.reject(new Error(`Unexpected API call: ${endpoint}`));
    });

    render(
      <WorkspaceServiceItem
        workspaceService={workspaceService}
        updateWorkspaceService={vi.fn()}
        removeWorkspaceService={vi.fn()}
      />,
      {
        children: null,
        initialEntries: ["/workspaces/test-workspace/workspace-services/test-service"],
      },
    );

    await waitFor(() => expect(screen.getByTestId("resource-card-list")).toBeInTheDocument());
    await showAllResources();
    expect(screen.getByTestId("resource-card-list")).toHaveTextContent("test-user-resource");
    expect(screen.queryByText("Error retrieving resources")).not.toBeInTheDocument();
  });

  const mockApi = (userResources: Array<any>) =>
    mockApiCall.mockImplementation((endpoint: string) => {
      if (endpoint.endsWith("/workspace-services/test-service")) return Promise.resolve({ workspaceService });
      if (endpoint.endsWith("/user-resources")) return Promise.resolve({ userResources });
      if (endpoint.endsWith("/user-resource-templates")) return Promise.resolve({ templates: [{}] });
      if (endpoint.endsWith("/users")) return Promise.resolve({ users: [] });
      return Promise.reject(new Error(`Unexpected API call: ${endpoint}`));
    });

  const renderItem = () =>
    render(
      <WorkspaceServiceItem
        workspaceService={workspaceService}
        updateWorkspaceService={vi.fn()}
        removeWorkspaceService={vi.fn()}
      />,
      {
        children: null,
        initialEntries: ["/workspaces/test-workspace/workspace-services/test-service"],
      },
    );

  it("defaults owners to their own resources", async () => {
    mockApi([{ id: "test-user-resource", ownerId: "someone-else" }]);
    renderItem();

    await waitFor(() => expect(screen.getByLabelText(/Showing my resources/)).toBeInTheDocument());
    expect(screen.getByRole("heading", { name: "Resources" })).toBeInTheDocument();
    expect(screen.getByText("You do not own any resources in this workspace service.")).toBeInTheDocument();

    await showAllResources();

    await waitFor(() => expect(screen.getByTestId("resource-card-list")).toHaveTextContent("test-user-resource"));
  });

  it("refreshes only the service and its user resources without remounting the list", async () => {
    mockApi([{ id: "test-user-resource" }]);
    (globalThis as any).resourceCardListMounts = 0;
    renderItem();
    await waitFor(() => expect(screen.getByTestId("resource-card-list")).toBeInTheDocument());
    await showAllResources();
    expect(screen.getByTestId("resource-card-list")).toHaveTextContent("test-user-resource");
    mockApiCall.mockClear();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    });

    await waitFor(() => expect(mockApiCall).toHaveBeenCalledTimes(2));
    const endpoints = mockApiCall.mock.calls.map((call) => call[0]);
    expect(endpoints.some((e: string) => e.endsWith("/user-resources"))).toBe(true);
    expect(endpoints.some((e: string) => e.endsWith("/workspace-services/test-service"))).toBe(true);
    expect((globalThis as any).resourceCardListMounts).toBe(1);
  });

  it("searches resources by name and owner", async () => {
    mockApi([
      { id: "vm-alpha", ownerId: "owner-a", properties: { display_name: "Alpha VM" } },
      { id: "vm-beta", ownerId: "owner-b", properties: { display_name: "Beta VM" } },
    ]);
    renderItem();
    await waitFor(() => expect(screen.getByTestId("resource-card-list")).toBeInTheDocument());
    await showAllResources();
    expect(screen.getByTestId("resource-card-list")).toHaveTextContent("vm-alpha,vm-beta");

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "beta" } });
    expect(screen.getByTestId("resource-card-list")).toHaveTextContent("vm-beta");
    expect(screen.getByTestId("resource-card-list")).not.toHaveTextContent("vm-alpha");

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "owner-a" } });
    expect(screen.getByTestId("resource-card-list")).toHaveTextContent("vm-alpha");
    expect(screen.getByTestId("resource-card-list")).not.toHaveTextContent("vm-beta");
  });
});

import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
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
  ResourceHeader: ({ resource }: any) => <div data-testid="resource-header">{resource.id}</div>,
}));

vi.mock("../shared/ResourceBody", () => ({
  ResourceBody: () => <div data-testid="resource-body" />,
}));

vi.mock("../shared/ResourceCardList", () => ({
  ResourceCardList: ({ resources }: any) => (
    <div data-testid="resource-card-list">{resources.map((resource: any) => resource.id).join(",")}</div>
  ),
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

    render(<WorkspaceServiceItem workspaceService={workspaceService} updateWorkspaceService={vi.fn()} removeWorkspaceService={vi.fn()} />, {
      children: null,
      initialEntries: ["/workspaces/test-workspace/workspace-services/test-service"],
    });

    await waitFor(() => expect(screen.getByTestId("resource-card-list")).toBeInTheDocument());
    expect(screen.getByTestId("resource-card-list")).toHaveTextContent("test-user-resource");
    expect(screen.queryByText("Error retrieving resources")).not.toBeInTheDocument();
  });
});

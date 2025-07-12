import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  render,
  screen,
  waitFor,
  createAuthApiCallMock,
  createApiEndpointsMock
} from "../../test-utils";
import { createCompleteFluentUIMock } from "../../test-utils/fluentui-mocks";
import { CostsTag } from "./CostsTag";
import { CostsContext } from "../../contexts/CostsContext";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { LoadingState } from "../../models/loadingState";
import { CostResource } from "../../models/costs";
import { ResourceType } from "../../models/resourceType";

// Mock the API hook using centralized utility
vi.mock("../../hooks/useAuthApiCall", () => {
  // Create the mock inside the factory function to avoid hoisting issues
  const mockApiCall = vi.fn();
  const mock = createAuthApiCallMock(mockApiCall);
  // Store a reference to the mock for tests to access
  (globalThis as any).__mockApiCall = mockApiCall;
  return mock;
});

// Mock API endpoints using centralized utility
vi.mock("../../models/apiEndpoints", () => createApiEndpointsMock());

// Mock FluentUI components using centralized mocks
vi.mock("@fluentui/react", () => {
  // Import directly to avoid hoisting issues
  return createCompleteFluentUIMock();
});

// Create proper mock workspace
const mockWorkspace = {
  id: "test-workspace-id",
  isEnabled: true,
  resourcePath: "/workspaces/test-workspace-id",
  resourceVersion: 1,
  resourceType: ResourceType.Workspace,
  templateName: "base",
  templateVersion: "1.0.0",
  availableUpgrades: [],
  deploymentStatus: "deployed",
  updatedWhen: Date.now(),
  history: [],
  _etag: "test-etag",
  properties: {
    display_name: "Test Workspace",
  },
  user: {
    id: "test-user-id",
    name: "Test User",
    email: "test@example.com",
    roleAssignments: [],
    roles: ["workspace_owner"],
  },
  workspaceURL: "https://workspace.example.com",
};


const createMockCostsContext = (costs?: CostResource[]) => ({
  costs,
  loadingState: LoadingState.Ok,
  setCosts: vi.fn(),
  setLoadingState: vi.fn(),
});

const createMockWorkspaceContext = (costs?: CostResource[]) => ({
  costs,
  workspace: mockWorkspace,
  workspaceApplicationIdURI: "test-app-id-uri",
  roles: ["workspace_researcher"],
  setCosts: vi.fn(),
  setRoles: vi.fn(),
  setWorkspace: vi.fn(),
});

const renderWithContexts = (
  component: React.ReactElement,
  costsContextCosts?: CostResource[],
  workspaceContextCosts?: CostResource[],
) => {
  const costsContext = createMockCostsContext(costsContextCosts);
  const workspaceContext = createMockWorkspaceContext(workspaceContextCosts);

  return render(
    <CostsContext.Provider value={costsContext as any}>
      <WorkspaceContext.Provider value={workspaceContext as any}>
        {component}
      </WorkspaceContext.Provider>
    </CostsContext.Provider>
  );
};

describe("CostsTag Component", () => {
  // Get a reference to the mock API call function
  const mockApiCall = (globalThis as any).__mockApiCall;

  beforeEach(() => {
    vi.clearAllMocks();
    mockApiCall.mockReset();
  });

  it("shows shimmer while loading", async () => {
    // Use a fresh mock for the API call
    const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
    mockApiCall.mockImplementation(async () => {
      await delay(100);
      return { workspaceAuth: { scopeId: "scope" }, costs: [{ cost: 123.45, currency: "USD" }], id: "resource1", name: "Resource 1" };
    });


    // Provide a workspace with id: undefined to trigger loading state
    const workspaceWithNoId = { ...mockWorkspace, id: undefined };
    const workspaceContext = {
      costs: undefined,
      workspace: workspaceWithNoId,
      workspaceApplicationIdURI: "test-app-id-uri",
      roles: ["workspace_researcher"],
      setCosts: vi.fn(),
      setRoles: vi.fn(),
      setWorkspace: vi.fn(),
    } as any;
    const costsContext = {
      costs: undefined,
      loadingState: LoadingState.Ok,
      setCosts: vi.fn(),
      setLoadingState: vi.fn(),
    } as any;
    render(
      <CostsContext.Provider value={costsContext}>
        <WorkspaceContext.Provider value={workspaceContext}>
          <CostsTag resourceId="resource1" />
        </WorkspaceContext.Provider>
      </CostsContext.Provider>
    );

    // Wait for shimmer to appear (async)
    expect(await screen.findByTestId("shimmer")).toBeInTheDocument();
  });

  it("displays formatted cost when available in workspace context", async () => {
    const workspaceCosts = [
      {
        id: "test-resource-id",
        name: "Test Resource",
        costs: [{ cost: 123.45, currency: "USD" }],
      },
    ];

    renderWithContexts(
      <CostsTag resourceId="test-resource-id" />,
      [], // costs context
      workspaceCosts, // workspace context
    );

    await waitFor(() => {
      expect(screen.getByText("$123.45")).toBeInTheDocument();
    });
  });

  it("displays formatted cost when available in costs context", async () => {
    const costsContextCosts = [
      {
        id: "test-resource-id",
        name: "Test Resource",
        costs: [{ cost: 67.89, currency: "EUR" }],
      },
    ];

    renderWithContexts(
      <CostsTag resourceId="test-resource-id" />,
      costsContextCosts, // costs context
      [], // workspace context
    );

    await waitFor(() => {
      expect(screen.getByText("€67.89")).toBeInTheDocument();
    });
  });

  it("displays clock icon when cost data is not available", async () => {
    const workspaceCosts = [
      {
        id: "test-resource-id",
        name: "Test Resource",
        costs: [], // No costs data
      },
    ];

    renderWithContexts(
      <CostsTag resourceId="test-resource-id" />,
      [], // costs context
      workspaceCosts, // workspace context
    );

    await waitFor(() => {
      expect(screen.getByTestId("icon-Clock")).toBeInTheDocument();
    });

    const tooltip = screen.getByTestId("tooltip");
    expect(tooltip).toHaveAttribute("title", "Cost data not yet available");
  });

  it("displays clock icon when resource is not found in costs", async () => {
    const workspaceCosts = [
      {
        id: "other-resource-id",
        name: "Other Resource",
        costs: [{ cost: 100, currency: "USD" }],
      },
    ];

    renderWithContexts(
      <CostsTag resourceId="test-resource-id" />,
      [], // costs context
      workspaceCosts, // workspace context
    );

    await waitFor(() => {
      expect(screen.getByTestId("icon-Clock")).toBeInTheDocument();
    });
  });

  it("formats currency with correct decimal places", async () => {
    const workspaceCosts = [
      {
        id: "test-resource-id",
        name: "Test Resource",
        costs: [{ cost: 123.456789, currency: "USD" }],
      },
    ];

    renderWithContexts(
      <CostsTag resourceId="test-resource-id" />,
      [], // costs context
      workspaceCosts, // workspace context
    );

    await waitFor(() => {
      expect(screen.getByText("$123.46")).toBeInTheDocument();
    });
  });

  it("prioritizes workspace costs over global costs context", async () => {
    const costsContextCosts = [
      {
        id: "test-resource-id",
        name: "Test Resource",
        costs: [{ cost: 100, currency: "EUR" }],
      },
    ];

    const workspaceCosts = [
      {
        id: "test-resource-id",
        name: "Test Resource",
        costs: [{ cost: 200, currency: "USD" }],
      },
    ];

    renderWithContexts(
      <CostsTag resourceId="test-resource-id" />,
      costsContextCosts, // costs context
      workspaceCosts, // workspace context
    );

    await waitFor(() => {
      // Should show workspace costs ($200), not global costs (€100)
      expect(screen.getByText("$200.00")).toBeInTheDocument();
    });
  });

  it("handles API errors gracefully", async () => {
    mockApiCall.mockRejectedValue(new Error("API Error"));

    renderWithContexts(<CostsTag resourceId="test-resource-id" />);

    // Should still eventually show clock icon when API fails
    await waitFor(() => {
      expect(screen.queryByTestId("shimmer")).not.toBeInTheDocument();
    });

    expect(screen.getByTestId("icon-Clock")).toBeInTheDocument();
  });
});

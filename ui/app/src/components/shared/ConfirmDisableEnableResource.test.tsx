import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, createPartialFluentUIMock } from "../../test-utils";
import { ConfirmDisableEnableResource } from "./ConfirmDisableEnableResource";
import { Resource } from "../../models/resource";
import { ResourceType } from "../../models/resourceType";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { CostResource } from "../../models/costs";

// Mock dependencies
const mockApiCall = vi.fn();
const mockDispatch = vi.fn();

vi.mock("../../hooks/useAuthApiCall", () => ({
  useAuthApiCall: () => mockApiCall,
  HttpMethod: { Patch: "PATCH" },
  ResultType: { JSON: "JSON" },
}));

vi.mock("../../hooks/customReduxHooks", () => ({
  useAppDispatch: () => mockDispatch,
}));

vi.mock("../shared/notifications/operationsSlice", () => ({
  addUpdateOperation: vi.fn(),
  default: (state: { items: unknown[] } = { items: [] }) => state
}));

// Mock FluentUI components using centralized mocks
vi.mock("@fluentui/react", async () => {
  const actual = await vi.importActual("@fluentui/react");
  return {
    ...actual,
    ...createPartialFluentUIMock([
      'Dialog',
      'DialogFooter',
      'DialogType',
      'PrimaryButton',
      'DefaultButton',
      'Spinner'
    ]),
  };
});

vi.mock("./ExceptionLayout", () => {
  const ExceptionLayout = ({ e }: any) => (
    <div data-testid="exception-layout">{e.userMessage}</div>
  );
  ExceptionLayout.displayName = 'ExceptionLayout';
  return { ExceptionLayout };
});

const mockResource: Resource = {
  id: "test-resource-id",
  resourceType: ResourceType.WorkspaceService,
  templateName: "test-template",
  templateVersion: "1.0.0",
  resourcePath: "/workspaces/test-workspace/workspace-services/test-resource-id",
  resourceVersion: 1,
  isEnabled: true,
  properties: {
    display_name: "Test Resource",
  },
  _etag: "test-etag",
  updatedWhen: Date.now(),
  deploymentStatus: "deployed",
  availableUpgrades: [],
  history: [],
  user: {
    id: "test-user-id",
    name: "Test User",
    email: "test@example.com",
    roleAssignments: [],
    roles: ["workspace_researcher"],
  },
};

const mockWorkspaceContext = {
  costs: [] as CostResource[],
  workspace: {
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
  },
  workspaceApplicationIdURI: "test-app-id-uri",
  roles: ["workspace_owner"],
  setCosts: vi.fn(),
  setRoles: vi.fn(),
  setWorkspace: vi.fn(),
};

const renderWithWorkspaceContext = (component: React.ReactElement) => {
  return render(
    <WorkspaceContext.Provider value={mockWorkspaceContext}>
      {component}
    </WorkspaceContext.Provider>
  );
};

describe("ConfirmDisableEnableResource Component", () => {
  const mockOnDismiss = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders disable dialog for enabled resource", () => {
    renderWithWorkspaceContext(
      <ConfirmDisableEnableResource
        resource={mockResource}
        isEnabled={false}
        onDismiss={mockOnDismiss}
      />
    );

    expect(screen.getByTestId("dialog-title")).toHaveTextContent(
      "Disable Resource?"
    );
    expect(screen.getByTestId("dialog-subtext")).toHaveTextContent(
      "Are you sure you want to disable Test Resource?"
    );
    expect(screen.getByTestId("primary-button")).toHaveTextContent("Disable");
  });

  it("renders enable dialog for disabled resource", () => {
    renderWithWorkspaceContext(
      <ConfirmDisableEnableResource
        resource={mockResource}
        isEnabled={true}
        onDismiss={mockOnDismiss}
      />
    );

    expect(screen.getByTestId("dialog-title")).toHaveTextContent(
      "Enable Resource?"
    );
    expect(screen.getByTestId("dialog-subtext")).toHaveTextContent(
      "Are you sure you want to enable Test Resource?"
    );
    expect(screen.getByTestId("primary-button")).toHaveTextContent("Enable");
  });

  it("calls onDismiss when cancel button is clicked", () => {
    renderWithWorkspaceContext(
      <ConfirmDisableEnableResource
        resource={mockResource}
        isEnabled={false}
        onDismiss={mockOnDismiss}
      />
    );

    fireEvent.click(screen.getByTestId("default-button"));
    expect(mockOnDismiss).toHaveBeenCalledTimes(1);
  });

  it("calls API and dispatches operation on confirmation", async () => {
    const mockOperation = { id: "operation-id", status: "running" };
    mockApiCall.mockResolvedValue({ operation: mockOperation });

    renderWithWorkspaceContext(
      <ConfirmDisableEnableResource
        resource={mockResource}
        isEnabled={false}
        onDismiss={mockOnDismiss}
      />
    );

    fireEvent.click(screen.getByTestId("primary-button"));

    await waitFor(() => {
      expect(mockApiCall).toHaveBeenCalledWith(
        mockResource.resourcePath,
        "PATCH",
        mockWorkspaceContext.workspaceApplicationIdURI,
        { isEnabled: false },
        "JSON",
        undefined,
        undefined,
        mockResource._etag
      );
    });

    expect(mockDispatch).toHaveBeenCalled();
    expect(mockOnDismiss).toHaveBeenCalled();
  });

  it("shows loading spinner during API call", async () => {
    mockApiCall.mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100))
    );

    renderWithWorkspaceContext(
      <ConfirmDisableEnableResource
        resource={mockResource}
        isEnabled={false}
        onDismiss={mockOnDismiss}
      />
    );

    fireEvent.click(screen.getByTestId("primary-button"));

    expect(screen.getByTestId("spinner")).toBeInTheDocument();
    expect(screen.getByText("Sending request...")).toBeInTheDocument();
  });

  it("displays error when API call fails", async () => {
    const error = new Error("Network error");
    mockApiCall.mockRejectedValue(error);

    renderWithWorkspaceContext(
      <ConfirmDisableEnableResource
        resource={mockResource}
        isEnabled={false}
        onDismiss={mockOnDismiss}
      />
    );

    fireEvent.click(screen.getByTestId("primary-button"));

    await waitFor(() => {
      expect(screen.getByTestId("exception-layout")).toBeInTheDocument();
      expect(screen.getByText("Failed to enable/disable resource")).toBeInTheDocument();
    });
  });

  it("uses workspace auth for workspace service resources", async () => {
    const mockOperation = { id: "operation-id", status: "running" };
    mockApiCall.mockResolvedValue({ operation: mockOperation });

    renderWithWorkspaceContext(
      <ConfirmDisableEnableResource
        resource={mockResource}
        isEnabled={false}
        onDismiss={mockOnDismiss}
      />
    );

    fireEvent.click(screen.getByTestId("primary-button"));

    await waitFor(() => {
      expect(mockApiCall).toHaveBeenCalledWith(
        expect.any(String),
        "PATCH",
        mockWorkspaceContext.workspaceApplicationIdURI, // should use workspace auth
        expect.any(Object),
        "JSON",
        undefined,
        undefined,
        expect.any(String)
      );
    });
  });

  it("does not use workspace auth for shared service resources", async () => {
    const sharedServiceResource = {
      ...mockResource,
      resourceType: ResourceType.SharedService,
    };
    const mockOperation = { id: "operation-id", status: "running" };
    mockApiCall.mockResolvedValue({ operation: mockOperation });

    renderWithWorkspaceContext(
      <ConfirmDisableEnableResource
        resource={sharedServiceResource}
        isEnabled={false}
        onDismiss={mockOnDismiss}
      />
    );

    fireEvent.click(screen.getByTestId("primary-button"));

    await waitFor(() => {
      expect(mockApiCall).toHaveBeenCalledWith(
        expect.any(String),
        "PATCH",
        undefined, // should not use workspace auth
        expect.any(Object),
        "JSON",
        undefined,
        undefined,
        expect.any(String)
      );
    });
  });
});

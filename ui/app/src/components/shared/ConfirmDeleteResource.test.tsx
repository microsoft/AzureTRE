import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, createPartialFluentUIMock, act } from "../../test-utils";
import { ConfirmDeleteResource } from "./ConfirmDeleteResource";
import { Resource } from "../../models/resource";
import { ResourceType } from "../../models/resourceType";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { LoadingState } from "../../models/loadingState";

// Mock the API hook
const mockApiCall = vi.fn();
vi.mock("../../hooks/useAuthApiCall", () => ({
  useAuthApiCall: () => mockApiCall,
  HttpMethod: { Delete: "DELETE" },
  ResultType: { JSON: "JSON" },
}));

// Mock addUpdateOperation function
const mockAddUpdateOperation = vi.fn();

vi.mock("../shared/notifications/operationsSlice", () => ({
  addUpdateOperation: (...args: any[]) => mockAddUpdateOperation(...args),
  default: (state: any = { items: [] }) => state
}));

// Mock FluentUI components - only the ones we need for this test
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

// Mock ExceptionLayout
vi.mock("./ExceptionLayout", () => ({
  ExceptionLayout: ({ e }: any) => (
    <div data-testid="exception-layout">
      Error: {e.userMessage || e.message}
    </div>
  ),
}));

const mockResource: Resource = {
  id: "test-resource-id",
  resourceType: ResourceType.Workspace,
  templateName: "test-template",
  templateVersion: "1.0.0",
  resourcePath: "/workspaces/test-resource-id",
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
  costs: [],
  workspace: {
    ...mockResource,
    workspaceURL: "https://workspace.example.com",
  },
  workspaceApplicationIdURI: "test-app-id-uri",
  roles: ["workspace_researcher"],
  setCosts: vi.fn(),
  setRoles: vi.fn(),
  setWorkspace: vi.fn(),
};

const createTestStore = () => {
  return configureStore({
    reducer: {
      operations: (state: any = { items: [] }) => state,
    },
  });
};

const renderWithContext = (component: React.ReactElement) => {
  const store = createTestStore();
  return render(
    <Provider store={store}>
      <WorkspaceContext.Provider value={mockWorkspaceContext}>
        {component}
      </WorkspaceContext.Provider>
    </Provider>
  );
};

describe("ConfirmDeleteResource Component", () => {
  const mockOnDismiss = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockAddUpdateOperation.mockReturnValue({ type: "operations/addUpdateOperation", payload: {} });
  });

  it("renders dialog with correct title and message", () => {
    renderWithContext(
      <ConfirmDeleteResource resource={mockResource} onDismiss={mockOnDismiss} />
    );

    expect(screen.getByTestId("dialog")).toBeInTheDocument();
    expect(screen.getByTestId("dialog-title")).toHaveTextContent("Delete Resource?");
    expect(screen.getByTestId("dialog-subtext")).toHaveTextContent(
      "Are you sure you want to permanently delete Test Resource?"
    );
  });

  it("renders delete and cancel buttons", () => {
    renderWithContext(
      <ConfirmDeleteResource resource={mockResource} onDismiss={mockOnDismiss} />
    );

    expect(screen.getByTestId("primary-button")).toHaveTextContent("Delete");
    expect(screen.getByTestId("default-button")).toHaveTextContent("Cancel");
  });

  it("calls onDismiss when cancel button is clicked", async () => {
    renderWithContext(
      <ConfirmDeleteResource resource={mockResource} onDismiss={mockOnDismiss} />
    );

    await act(async () => {
      fireEvent.click(screen.getByTestId("default-button"));
    });
    expect(mockOnDismiss).toHaveBeenCalledTimes(1);
  });

  it("calls onDismiss when close button is clicked", async () => {
    renderWithContext(
      <ConfirmDeleteResource resource={mockResource} onDismiss={mockOnDismiss} />
    );

    await act(async () => {
      fireEvent.click(screen.getByTestId("dialog-close"));
    });
    expect(mockOnDismiss).toHaveBeenCalledTimes(1);
  });

  it("shows spinner while deletion is in progress", async () => {
    // Mock API call to never resolve to keep loading state
    mockApiCall.mockImplementation(() => new Promise(() => { }));

    renderWithContext(
      <ConfirmDeleteResource resource={mockResource} onDismiss={mockOnDismiss} />
    );

    await act(async () => {
      fireEvent.click(screen.getByTestId("primary-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("spinner")).toBeInTheDocument();
    });

    expect(screen.getByTestId("spinner")).toHaveTextContent("Sending request...");
    expect(screen.queryByTestId("dialog-footer")).not.toBeInTheDocument();
  });

  it("calls API delete and dispatches operation on successful deletion", async () => {
    const mockOperation = { id: "test-operation-id", resourceId: "test-resource-id" };
    mockApiCall.mockResolvedValue({ operation: mockOperation });

    renderWithContext(
      <ConfirmDeleteResource resource={mockResource} onDismiss={mockOnDismiss} />
    );

    await act(async () => {
      fireEvent.click(screen.getByTestId("primary-button"));
    });

    await waitFor(() => {
      expect(mockApiCall).toHaveBeenCalledWith(
        "/workspaces/test-resource-id",
        "DELETE",
        undefined, // not a workspace service, so no auth
        undefined,
        "JSON"
      );
    });

    expect(mockAddUpdateOperation).toHaveBeenCalledWith(mockOperation);
    expect(mockOnDismiss).toHaveBeenCalledTimes(1);
  });

  it("uses workspace auth for workspace service resources", async () => {
    const workspaceServiceResource = {
      ...mockResource,
      resourceType: ResourceType.WorkspaceService,
    };

    const mockOperation = { id: "test-operation-id", resourceId: "test-resource-id" };
    mockApiCall.mockResolvedValue({ operation: mockOperation });

    renderWithContext(
      <ConfirmDeleteResource
        resource={workspaceServiceResource}
        onDismiss={mockOnDismiss}
      />
    );

    await act(async () => {
      fireEvent.click(screen.getByTestId("primary-button"));
    });

    await waitFor(() => {
      expect(mockApiCall).toHaveBeenCalledWith(
        "/workspaces/test-resource-id",
        "DELETE",
        "test-app-id-uri", // should use workspace auth
        undefined,
        "JSON"
      );
    });
  });

  it("uses workspace auth for user resource resources", async () => {
    const userResource = {
      ...mockResource,
      resourceType: ResourceType.UserResource,
    };

    const mockOperation = { id: "test-operation-id", resourceId: "test-resource-id" };
    mockApiCall.mockResolvedValue({ operation: mockOperation });

    renderWithContext(
      <ConfirmDeleteResource resource={userResource} onDismiss={mockOnDismiss} />
    );

    await act(async () => {
      fireEvent.click(screen.getByTestId("primary-button"));
    });

    await waitFor(() => {
      expect(mockApiCall).toHaveBeenCalledWith(
        "/workspaces/test-resource-id",
        "DELETE",
        "test-app-id-uri", // should use workspace auth
        undefined,
        "JSON"
      );
    });
  });

  it("shows error when deletion fails", async () => {
    const errorMessage = "Failed to delete resource";
    mockApiCall.mockRejectedValue(new Error("Network error"));

    renderWithContext(
      <ConfirmDeleteResource resource={mockResource} onDismiss={mockOnDismiss} />
    );

    await act(async () => {
      fireEvent.click(screen.getByTestId("primary-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("exception-layout")).toBeInTheDocument();
    });

    expect(screen.getByTestId("exception-layout")).toHaveTextContent(
      "Error: Failed to delete resource"
    );
  });

  it("does not call onDismiss when deletion fails", async () => {
    mockApiCall.mockRejectedValue(new Error("Network error"));

    renderWithContext(
      <ConfirmDeleteResource resource={mockResource} onDismiss={mockOnDismiss} />
    );

    await act(async () => {
      fireEvent.click(screen.getByTestId("primary-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("exception-layout")).toBeInTheDocument();
    });

    expect(mockOnDismiss).not.toHaveBeenCalled();
  });
});

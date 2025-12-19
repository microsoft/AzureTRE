import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, createPartialFluentUIMock } from "../../test-utils";
import { ConfirmUpgradeResource } from "./ConfirmUpgradeResource";
import { Resource, AvailableUpgrade } from "../../models/resource";
import { ResourceType } from "../../models/resourceType";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { CostResource } from "../../models/costs";

// Mock dependencies
const mockApiCall = vi.fn();
const mockDispatch = vi.fn();

// Mock template schemas
const mockCurrentTemplateSchema = {
  properties: {
    display_name: { type: "string" },
    resource_key: { type: "string" },
    existing_property: { type: "string" },
  },
  required: ["display_name"],
};

const mockNewTemplateSchema = {
  properties: {
    display_name: { type: "string" },
    resource_key: { type: "string" },
    new_property: { type: "string", default: "default_value" },
  },
  required: ["display_name"],
  uiSchema: {},
};

vi.mock("../../hooks/useAuthApiCall", () => ({
  useAuthApiCall: () => mockApiCall,
  HttpMethod: { Patch: "PATCH", Get: "GET" },
  ResultType: { JSON: "JSON" },
}));

vi.mock("../../hooks/customReduxHooks", () => ({
  useAppDispatch: () => mockDispatch,
}));

vi.mock("../shared/notifications/operationsSlice", () => ({
  addUpdateOperation: vi.fn(),
  default: (state: any = { items: [] }) => state
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
      'Dropdown',
      'Spinner',
      'MessageBar',
      'MessageBarType',
      'Icon'
    ]),
  };
});

vi.mock("./ExceptionLayout", () => ({
  ExceptionLayout: ({ e }: any) => (
    <div data-testid="exception-layout">{e.userMessage}</div>
  ),
}));

const mockAvailableUpgrades: AvailableUpgrade[] = [
  { version: "1.1.0", forceUpdateRequired: false },
  { version: "1.2.0", forceUpdateRequired: false },
  { version: "2.0.0", forceUpdateRequired: true },
];

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
  availableUpgrades: mockAvailableUpgrades,
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

describe("ConfirmUpgradeResource Component", () => {
  const mockOnDismiss = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock API call to return templates for GET requests
    mockApiCall.mockImplementation((url, method) => {
      if (method === "GET" && url.includes("?version=")) {
        if (url.includes("version=1.0.0")) {
          return Promise.resolve(mockCurrentTemplateSchema);
        } else {
          return Promise.resolve(mockNewTemplateSchema);
        }
      }
      return Promise.resolve({ operation: { id: "operation-id", status: "running" } });
    });
  });

  it("renders upgrade dialog with correct title and content", () => {
    renderWithWorkspaceContext(
      <ConfirmUpgradeResource
        resource={mockResource}
        onDismiss={mockOnDismiss}
      />
    );

    expect(screen.getByTestId("dialog-title")).toHaveTextContent(
      "Upgrade Template Version?"
    );
    expect(screen.getByTestId("dialog-subtext")).toHaveTextContent(
      "Are you sure you want upgrade the template version of Test Resource from version 1.0.0?"
    );
  });

  it("shows warning message about irreversible upgrade", () => {
    renderWithWorkspaceContext(
      <ConfirmUpgradeResource
        resource={mockResource}
        onDismiss={mockOnDismiss}
      />
    );

    expect(screen.getByTestId("message-bar")).toBeInTheDocument();
    expect(screen.getByText("Upgrading the template version is irreversible.")).toBeInTheDocument();
  });

  it("renders dropdown with available upgrade versions", () => {
    renderWithWorkspaceContext(
      <ConfirmUpgradeResource
        resource={mockResource}
        onDismiss={mockOnDismiss}
      />
    );

    const dropdown = screen.getByTestId("dropdown");
    expect(dropdown).toBeInTheDocument();

    // Check that non-major upgrades are included (force update required = false)
    expect(screen.getByText("1.1.0")).toBeInTheDocument();
    expect(screen.getByText("1.2.0")).toBeInTheDocument();

    // Major upgrade (force update required = true) should not be included in regular dropdown
    expect(screen.queryByText("2.0.0")).not.toBeInTheDocument();
  });

  it("disables upgrade button when no version is selected", () => {
    renderWithWorkspaceContext(
      <ConfirmUpgradeResource
        resource={mockResource}
        onDismiss={mockOnDismiss}
      />
    );

    const upgradeButton = screen.getByTestId("primary-button");
    expect(upgradeButton).toBeDisabled();
  });

  it("enables upgrade button when version is selected", async () => {
    renderWithWorkspaceContext(
      <ConfirmUpgradeResource
        resource={mockResource}
        onDismiss={mockOnDismiss}
      />
    );

    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    // Wait for schema to load and button to become enabled
    await waitFor(() => {
      const upgradeButton = screen.getByTestId("primary-button");
      expect(upgradeButton).not.toBeDisabled();
    });
  });

  it("calls API with selected version on upgrade", async () => {
    const mockOperation = { id: "operation-id", status: "running" };
    mockApiCall.mockImplementation((url, method) => {
      if (method === "PATCH") {
        return Promise.resolve({ operation: mockOperation });
      }
      // Handle GET requests for schemas
      if (method === "GET" && url.includes("?version=")) {
        if (url.includes("version=1.0.0")) {
          return Promise.resolve(mockCurrentTemplateSchema);
        } else {
          return Promise.resolve(mockNewTemplateSchema);
        }
      }
      return Promise.resolve({ operation: mockOperation });
    });

    renderWithWorkspaceContext(
      <ConfirmUpgradeResource
        resource={mockResource}
        onDismiss={mockOnDismiss}
      />
    );

    // Select a version
    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    // Wait for schema to load
    await waitFor(() => {
      expect(screen.queryByText("Loading new template schema...")).not.toBeInTheDocument();
    });

    // Click upgrade
    const upgradeButton = screen.getByTestId("primary-button");
    fireEvent.click(upgradeButton);

    await waitFor(() => {
      expect(mockApiCall).toHaveBeenCalledWith(
        mockResource.resourcePath,
        "PATCH",
        mockWorkspaceContext.workspaceApplicationIdURI,
        expect.objectContaining({
          templateVersion: "1.1.0",
          properties: expect.any(Object),
        }),
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
    mockApiCall.mockImplementation((url, method) => {
      if (method === "PATCH") {
        return new Promise((resolve) =>
          setTimeout(
            () => {
              resolve({ operation: { id: "operation-id", status: "running" } });
            },
            100
          )
        );
      }
      // Handle GET requests for schemas
      if (method === "GET" && url.includes("?version=")) {
        if (url.includes("version=1.0.0")) {
          return Promise.resolve(mockCurrentTemplateSchema);
        } else {
          return Promise.resolve(mockNewTemplateSchema);
        }
      }
      return Promise.resolve({
        operation: { id: "operation-id", status: "running" },
      });
    });

    renderWithWorkspaceContext(
      <ConfirmUpgradeResource
        resource={mockResource}
        onDismiss={mockOnDismiss}
      />
    );

    // Select a version
    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    // Wait for schema to load
    await waitFor(() => {
      expect(
        screen.queryByText("Loading new template schema...")
      ).not.toBeInTheDocument();
    });

    // Click upgrade and check for loading spinner
    const upgradeButton = screen.getByTestId("primary-button");
    fireEvent.click(upgradeButton);

    expect(screen.getByTestId("spinner")).toBeInTheDocument();
    expect(screen.getByText("Sending request...")).toBeInTheDocument();
  });

  it("displays error when API call fails", async () => {
    mockApiCall.mockImplementation((url, method) => {
      if (method === "PATCH") {
        return Promise.reject(new Error("Network error"));
      }
      // Handle GET requests for schemas
      if (method === "GET" && url.includes("?version=")) {
        if (url.includes("version=1.0.0")) {
          return Promise.resolve(mockCurrentTemplateSchema);
        } else {
          return Promise.resolve(mockNewTemplateSchema);
        }
      }
      return Promise.reject(new Error("Network error"));
    });

    renderWithWorkspaceContext(
      <ConfirmUpgradeResource
        resource={mockResource}
        onDismiss={mockOnDismiss}
      />
    );

    // Select a version
    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    // Wait for schema to load
    await waitFor(() => {
      expect(
        screen.queryByText("Loading new template schema...")
      ).not.toBeInTheDocument();
    });

    // Click upgrade
    const upgradeButton = screen.getByTestId("primary-button");
    fireEvent.click(upgradeButton);

    await waitFor(() => {
      expect(screen.getByTestId("exception-layout")).toBeInTheDocument();
      expect(screen.getByText("Failed to upgrade resource")).toBeInTheDocument();
    });
  });

  it("uses workspace auth for workspace service resources", async () => {
    const mockOperation = { id: "operation-id", status: "running" };
    mockApiCall.mockImplementation((url, method) => {
      if (method === "PATCH") {
        return Promise.resolve({ operation: mockOperation });
      }
      // Handle GET requests for schemas
      if (method === "GET" && url.includes("?version=")) {
        if (url.includes("version=1.0.0")) {
          return Promise.resolve(mockCurrentTemplateSchema);
        } else {
          return Promise.resolve(mockNewTemplateSchema);
        }
      }
      return Promise.resolve({ operation: mockOperation });
    });

    renderWithWorkspaceContext(
      <ConfirmUpgradeResource
        resource={mockResource}
        onDismiss={mockOnDismiss}
      />
    );

    // Select a version
    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    // Wait for schema to load
    await waitFor(() => {
      expect(
        screen.queryByText("Loading new template schema...")
      ).not.toBeInTheDocument();
    });

    // Click upgrade
    const upgradeButton = screen.getByTestId("primary-button");
    fireEvent.click(upgradeButton);

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
    mockApiCall.mockImplementation((url, method) => {
      if (method === "PATCH") {
        return Promise.resolve({ operation: mockOperation });
      }
      // Handle GET requests for schemas
      if (method === "GET" && url.includes("?version=")) {
        if (url.includes("version=1.0.0")) {
          return Promise.resolve(mockCurrentTemplateSchema);
        } else {
          return Promise.resolve(mockNewTemplateSchema);
        }
      }
      return Promise.resolve({ operation: mockOperation });
    });

    renderWithWorkspaceContext(
      <ConfirmUpgradeResource
        resource={sharedServiceResource}
        onDismiss={mockOnDismiss}
      />
    );

    // Select a version
    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    // Wait for schema to load
    await waitFor(() => {
      expect(
        screen.queryByText("Loading new template schema...")
      ).not.toBeInTheDocument();
    });

    // Click upgrade
    const upgradeButton = screen.getByTestId("primary-button");
    fireEvent.click(upgradeButton);

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

  it("filters out major upgrades from dropdown options", () => {
    const resourceWithMajorUpgrade = {
      ...mockResource,
      availableUpgrades: [
        { version: "1.1.0", forceUpdateRequired: false },
        { version: "2.0.0", forceUpdateRequired: true },
        { version: "1.2.0", forceUpdateRequired: false },
      ],
    };

    renderWithWorkspaceContext(
      <ConfirmUpgradeResource
        resource={resourceWithMajorUpgrade}
        onDismiss={mockOnDismiss}
      />
    );

    // Minor updates should be available
    expect(screen.getByText("1.1.0")).toBeInTheDocument();
    expect(screen.getByText("1.2.0")).toBeInTheDocument();

    // Major update should not be available in dropdown
    expect(screen.queryByText("2.0.0")).not.toBeInTheDocument();
  });

  it("displays form when new properties need to be added", async () => {
    renderWithWorkspaceContext(
      <ConfirmUpgradeResource
        resource={mockResource}
        onDismiss={mockOnDismiss}
      />
    );

    // Select a version that has new properties
    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    // Wait for schema to load
    await waitFor(() => {
      expect(
        screen.queryByText("Loading new template schema...")
      ).not.toBeInTheDocument();
    });

    // Should show info message about new properties
    expect(screen.getByText("You must specify values for new properties:")).toBeInTheDocument();

    // The form input for new_property should be rendered
    expect(screen.getByDisplayValue("default_value")).toBeInTheDocument();
  });

  it("displays warning about removed properties", async () => {
    renderWithWorkspaceContext(
      <ConfirmUpgradeResource
        resource={mockResource}
        onDismiss={mockOnDismiss}
      />
    );

    // Select a version
    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    // Wait for schema to load
    await waitFor(() => {
      expect(
        screen.queryByText("Loading new template schema...")
      ).not.toBeInTheDocument();
    });

    // Should show warning about removed properties
    expect(screen.getByText(/Warning: The following properties are no longer present/)).toBeInTheDocument();
    expect(screen.getByText(/existing_property/)).toBeInTheDocument();
  });

  it("disables upgrade button when required new properties are cleared", async () => {
    renderWithWorkspaceContext(
      <ConfirmUpgradeResource
        resource={mockResource}
        onDismiss={mockOnDismiss}
      />
    );

    // Select a version
    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    // Wait for schema to load
    await waitFor(() => {
      expect(
        screen.queryByText("Loading new template schema...")
      ).not.toBeInTheDocument();
    });

    // Find the input field and clear it
    const inputField = screen.getByDisplayValue("default_value");
    fireEvent.change(inputField, { target: { value: "" } });

    // Button should now be disabled because the required property is empty
    await waitFor(() => {
      const upgradeButton = screen.getByTestId("primary-button");
      expect(upgradeButton).toBeDisabled();
    });
  });

  it("enables upgrade button when all new properties are filled in", async () => {
    renderWithWorkspaceContext(
      <ConfirmUpgradeResource
        resource={mockResource}
        onDismiss={mockOnDismiss}
      />
    );

    // Select a version
    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    // Wait for schema to load
    await waitFor(() => {
      expect(
        screen.queryByText("Loading new template schema...")
      ).not.toBeInTheDocument();
    });

    // Find the new_property input field and fill it
    const inputField = screen.getByDisplayValue("default_value");
    fireEvent.change(inputField, { target: { value: "filled_value" } });

    // Button should now be enabled
    await waitFor(() => {
      const upgradeButton = screen.getByTestId("primary-button");
      expect(upgradeButton).not.toBeDisabled();
    });
  });

  it("includes new property values in upgrade API call", async () => {
    const mockOperation = { id: "operation-id", status: "running" };
    mockApiCall.mockImplementation((url, method) => {
      if (method === "PATCH") {
        return Promise.resolve({ operation: mockOperation });
      }
      // Handle GET requests for schemas
      if (method === "GET" && url.includes("?version=")) {
        if (url.includes("version=1.0.0")) {
          return Promise.resolve(mockCurrentTemplateSchema);
        } else {
          return Promise.resolve(mockNewTemplateSchema);
        }
      }
      return Promise.resolve({ operation: mockOperation });
    });

    renderWithWorkspaceContext(
      <ConfirmUpgradeResource
        resource={mockResource}
        onDismiss={mockOnDismiss}
      />
    );

    // Select a version
    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    // Wait for schema to load
    await waitFor(() => {
      expect(
        screen.queryByText("Loading new template schema...")
      ).not.toBeInTheDocument();
    });

    // Fill in the new property
    const inputField = screen.getByDisplayValue("default_value");
    fireEvent.change(inputField, { target: { value: "custom_value" } });

    // Click upgrade
    await waitFor(() => {
      const upgradeButton = screen.getByTestId("primary-button");
      fireEvent.click(upgradeButton);
    });

    // Verify the API call includes the new property value
    await waitFor(() => {
      expect(mockApiCall).toHaveBeenCalledWith(
        mockResource.resourcePath,
        "PATCH",
        mockWorkspaceContext.workspaceApplicationIdURI,
        expect.objectContaining({
          templateVersion: "1.1.0",
          properties: expect.objectContaining({
            new_property: "custom_value",
          }),
        }),
        "JSON",
        undefined,
        undefined,
        mockResource._etag
      );
    });
  });
});

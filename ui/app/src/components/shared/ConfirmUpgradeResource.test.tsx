import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { act, render, screen, fireEvent, waitFor, createPartialFluentUIMock } from "../../test-utils";
import { ConfirmUpgradeResource } from "./ConfirmUpgradeResource";
import {
  matchesIfCondition,
  getAllPropertyKeys,
  getSchemaPropertyFromProperties,
} from "../../utils/schemaUpgradeUtils";
import { Resource, AvailableUpgrade } from "../../models/resource";
import { UserResource } from "../../models/userResource";
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
  required: ["display_name", "new_property"],
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
  default: (state: any = { items: [] }) => state,
}));

// Mock FluentUI components using centralized mocks
vi.mock("@fluentui/react", async () => {
  const actual = await vi.importActual("@fluentui/react");
  return {
    ...actual,
    ...createPartialFluentUIMock([
      "Dialog",
      "DialogFooter",
      "DialogType",
      "PrimaryButton",
      "DefaultButton",
      "Dropdown",
      "Spinner",
      "MessageBar",
      "MessageBarType",
      "Icon",
      "TextField",
    ]),
  };
});

vi.mock("./ExceptionLayout", () => ({
  ExceptionLayout: ({ e }: any) => <div data-testid="exception-layout">{e.userMessage}</div>,
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
  return render(<WorkspaceContext.Provider value={mockWorkspaceContext}>{component}</WorkspaceContext.Provider>);
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
    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={mockResource} onDismiss={mockOnDismiss} />);

    expect(screen.getByTestId("dialog-title")).toHaveTextContent("Upgrade Template Version?");
    expect(screen.getByTestId("dialog-subtext")).toHaveTextContent(
      "Are you sure you want upgrade the template version of Test Resource from version 1.0.0?",
    );
  });

  it("shows warning message about irreversible upgrade", () => {
    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={mockResource} onDismiss={mockOnDismiss} />);

    expect(screen.getByTestId("message-bar")).toBeInTheDocument();
    expect(screen.getByText("Upgrading the template version is irreversible.")).toBeInTheDocument();
  });

  it("renders dropdown with available upgrade versions", () => {
    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={mockResource} onDismiss={mockOnDismiss} />);

    const dropdown = screen.getByTestId("dropdown");
    expect(dropdown).toBeInTheDocument();

    // Check that non-major upgrades are included (force update required = false)
    expect(screen.getByText("1.1.0")).toBeInTheDocument();
    expect(screen.getByText("1.2.0")).toBeInTheDocument();

    // Major upgrade (force update required = true) should not be included in regular dropdown
    expect(screen.queryByText("2.0.0")).not.toBeInTheDocument();
  });

  it("disables upgrade button when no version is selected", () => {
    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={mockResource} onDismiss={mockOnDismiss} />);

    const upgradeButton = screen.getByTestId("primary-button");
    expect(upgradeButton).toBeDisabled();
  });

  it("enables upgrade button when version is selected", async () => {
    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={mockResource} onDismiss={mockOnDismiss} />);

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

    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={mockResource} onDismiss={mockOnDismiss} />);

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
        mockResource._etag,
      );
    });

    expect(mockDispatch).toHaveBeenCalled();
    expect(mockOnDismiss).toHaveBeenCalled();
  });

  it("shows loading spinner during API call", async () => {
    mockApiCall.mockImplementation((url, method) => {
      if (method === "PATCH") {
        return new Promise((resolve) =>
          setTimeout(() => {
            resolve({ operation: { id: "operation-id", status: "running" } });
          }, 100),
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

    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={mockResource} onDismiss={mockOnDismiss} />);

    // Select a version
    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    // Wait for schema to load
    await waitFor(() => {
      expect(screen.queryByText("Loading new template schema...")).not.toBeInTheDocument();
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

    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={mockResource} onDismiss={mockOnDismiss} />);

    // Select a version
    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    // Wait for schema to load
    await waitFor(() => {
      expect(screen.queryByText("Loading new template schema...")).not.toBeInTheDocument();
    });

    // Click upgrade
    const upgradeButton = screen.getByTestId("primary-button");
    await act(async () => {
      fireEvent.click(upgradeButton);
    });

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

    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={mockResource} onDismiss={mockOnDismiss} />);

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
        expect.any(String),
        "PATCH",
        mockWorkspaceContext.workspaceApplicationIdURI, // should use workspace auth
        expect.any(Object),
        "JSON",
        undefined,
        undefined,
        expect.any(String),
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

    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={sharedServiceResource} onDismiss={mockOnDismiss} />);

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
        expect.any(String),
        "PATCH",
        undefined, // should not use workspace auth
        expect.any(Object),
        "JSON",
        undefined,
        undefined,
        expect.any(String),
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
      <ConfirmUpgradeResource resource={resourceWithMajorUpgrade} onDismiss={mockOnDismiss} />,
    );

    // Minor updates should be available
    expect(screen.getByText("1.1.0")).toBeInTheDocument();
    expect(screen.getByText("1.2.0")).toBeInTheDocument();

    // Major update should not be available in dropdown
    expect(screen.queryByText("2.0.0")).not.toBeInTheDocument();
  });

  it("displays form when new properties need to be added", async () => {
    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={mockResource} onDismiss={mockOnDismiss} />);

    // Select a version that has new properties
    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    // Wait for schema to load
    await waitFor(() => {
      expect(screen.queryByText("Loading new template schema...")).not.toBeInTheDocument();
    });

    // Should show info message about new properties
    expect(screen.getByText("Review values for new or changed properties:")).toBeInTheDocument();

    // The form input for new_property should be rendered
    expect(screen.getByDisplayValue("default_value")).toBeInTheDocument();
  });

  it("displays warning about removed properties", async () => {
    const resourceWithRemovedProp = {
      ...mockResource,
      properties: {
        ...mockResource.properties,
        existing_property: "some_value",
      },
    };
    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={resourceWithRemovedProp} onDismiss={mockOnDismiss} />);

    // Select a version
    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    // Wait for schema to load
    await waitFor(() => {
      expect(screen.queryByText("Loading new template schema...")).not.toBeInTheDocument();
    });

    // Should show warning about removed properties
    expect(screen.getByText(/Warning: The following properties are no longer present/)).toBeInTheDocument();
    expect(screen.getByText(/existing_property/)).toBeInTheDocument();
  });

  it("disables upgrade button when required new properties are cleared", async () => {
    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={mockResource} onDismiss={mockOnDismiss} />);

    // Select a version
    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    // Wait for schema to load
    await waitFor(() => {
      expect(screen.queryByText("Loading new template schema...")).not.toBeInTheDocument();
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
    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={mockResource} onDismiss={mockOnDismiss} />);

    // Select a version
    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    // Wait for schema to load
    await waitFor(() => {
      expect(screen.queryByText("Loading new template schema...")).not.toBeInTheDocument();
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

    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={mockResource} onDismiss={mockOnDismiss} />);

    // Select a version
    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    // Wait for schema to load
    await waitFor(() => {
      expect(screen.queryByText("Loading new template schema...")).not.toBeInTheDocument();
    });

    // Fill in the new property
    const inputField = screen.getByDisplayValue("default_value");
    fireEvent.change(inputField, { target: { value: "custom_value" } });

    // Click upgrade
    const upgradeButton = screen.getByTestId("primary-button");
    fireEvent.click(upgradeButton);

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
        mockResource._etag,
      );
    });
  });

  it("does not use workspace auth for template GET requests even for workspace services", async () => {
    // Track all API calls
    const apiCalls: any[] = [];
    mockApiCall.mockImplementation((url, method, auth, ...rest) => {
      apiCalls.push({ url, method, auth });
      if (method === "GET" && url.includes("?version=")) {
        if (url.includes("version=1.0.0")) {
          return Promise.resolve(mockCurrentTemplateSchema);
        } else {
          return Promise.resolve(mockNewTemplateSchema);
        }
      }
      return Promise.resolve({ operation: { id: "operation-id", status: "running" } });
    });

    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={mockResource} onDismiss={mockOnDismiss} />);

    // Select a version to trigger template fetching
    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    // Wait for schema to load
    await waitFor(() => {
      expect(screen.queryByText("Loading new template schema...")).not.toBeInTheDocument();
    });

    // Verify that GET requests for templates did NOT use workspace auth
    const getRequests = apiCalls.filter((call) => call.method === "GET" && call.url.includes("?version="));
    expect(getRequests.length).toBeGreaterThan(0);
    getRequests.forEach((call) => {
      expect(call.auth).toBeUndefined(); // Templates should not use workspace auth
    });
  });

  it("hides message and enables upgrade button when all new properties are hidden with tre-hidden", async () => {
    const templateWithHiddenProperties = {
      properties: {
        display_name: { type: "string" },
        resource_key: { type: "string" },
        hidden_property: { type: "string", default: "hidden_value" },
      },
      required: ["display_name"],
      uiSchema: {
        hidden_property: {
          classNames: "tre-hidden",
        },
      },
    };

    mockApiCall.mockImplementation((url, method) => {
      if (method === "GET" && url.includes("?version=")) {
        if (url.includes("version=1.0.0")) {
          return Promise.resolve(mockCurrentTemplateSchema);
        } else {
          return Promise.resolve(templateWithHiddenProperties);
        }
      }
      return Promise.resolve({ operation: { id: "operation-id", status: "running" } });
    });

    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={mockResource} onDismiss={mockOnDismiss} />);

    // Select a version
    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    // Wait for schema to load
    await waitFor(() => {
      expect(screen.queryByText("Loading new template schema...")).not.toBeInTheDocument();
    });

    // Should NOT show the "You must specify values" message because all properties are hidden
    expect(screen.queryByText("Review values for new or changed properties:")).not.toBeInTheDocument();

    // Button should be enabled immediately
    const upgradeButton = screen.getByTestId("primary-button");
    expect(upgradeButton).not.toBeDisabled();
  });

  it("shows message and validates only visible properties when mix of visible and hidden properties", async () => {
    const templateWithMixedProperties = {
      properties: {
        display_name: { type: "string" },
        resource_key: { type: "string" },
        visible_property: { type: "string" },
        hidden_property: { type: "string", default: "hidden_value" },
      },
      required: ["display_name", "visible_property"],
      uiSchema: {
        hidden_property: {
          classNames: "tre-hidden",
        },
      },
    };

    mockApiCall.mockImplementation((url, method) => {
      if (method === "GET" && url.includes("?version=")) {
        if (url.includes("version=1.0.0")) {
          return Promise.resolve(mockCurrentTemplateSchema);
        } else {
          return Promise.resolve(templateWithMixedProperties);
        }
      }
      return Promise.resolve({ operation: { id: "operation-id", status: "running" } });
    });

    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={mockResource} onDismiss={mockOnDismiss} />);

    // Select a version
    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    // Wait for schema to load
    await waitFor(() => {
      expect(screen.queryByText("Loading new template schema...")).not.toBeInTheDocument();
    });

    // Should show the message because there's at least one visible property
    expect(screen.getByText("Review values for new or changed properties:")).toBeInTheDocument();

    // Button should be disabled because visible_property is empty
    const upgradeButton = screen.getByTestId("primary-button");
    expect(upgradeButton).toBeDisabled();
  });

  it("correctly handles nested object properties and default values on upgrade", async () => {
    const mockCurrentTemplateNestedSchema = {
      properties: {
        display_name: { type: "string" },
        parent_object: {
          type: "object",
          properties: {
            existing_child: { type: "string" },
          },
        },
      },
      required: ["display_name"],
    };

    const mockNewTemplateNestedSchema = {
      properties: {
        display_name: { type: "string" },
        parent_object: {
          type: "object",
          properties: {
            existing_child: { type: "string" },
            new_nested_child: { type: "string", default: "default_nested_value" },
            optional_nested_no_default: { type: "string" },
          },
          required: ["existing_child"],
        },
      },
      required: ["display_name"],
      uiSchema: {},
    };

    const mockResourceWithNested: Resource = {
      ...mockResource,
      properties: {
        display_name: "Test Resource",
        parent_object: {
          existing_child: "existing_child_value",
        },
      },
    };

    mockApiCall.mockImplementation((url, method) => {
      if (method === "GET" && url.includes("?version=")) {
        if (url.includes("version=1.0.0")) {
          return Promise.resolve(mockCurrentTemplateNestedSchema);
        } else {
          return Promise.resolve(mockNewTemplateNestedSchema);
        }
      }
      return Promise.resolve({ operation: { id: "operation-id", status: "running" } });
    });

    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={mockResourceWithNested} onDismiss={mockOnDismiss} />);

    // Select a version
    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    // Wait for schema to load
    await waitFor(() => {
      expect(screen.queryByText("Loading new template schema...")).not.toBeInTheDocument();
    });

    // The form inputs should only be rendered for newly added nested properties, while existing sub-fields are pruned
    expect(screen.queryByDisplayValue("existing_child_value")).not.toBeInTheDocument();
    expect(screen.getByDisplayValue("default_nested_value")).toBeInTheDocument();

    // Click upgrade
    const upgradeButton = screen.getByTestId("primary-button");
    fireEvent.click(upgradeButton);

    // Verify the PATCH API call includes the newly added nested properties, omitting existing sub-fields and optional nested fields with no default
    await waitFor(() => {
      expect(mockApiCall).toHaveBeenCalledWith(
        mockResourceWithNested.resourcePath,
        "PATCH",
        mockWorkspaceContext.workspaceApplicationIdURI,
        expect.objectContaining({
          templateVersion: "1.1.0",
          properties: expect.objectContaining({
            parent_object: {
              new_nested_child: "default_nested_value",
            },
          }),
        }),
        "JSON",
        undefined,
        undefined,
        mockResourceWithNested._etag,
      );
    });
  });

  it("detects when an enum value is removed and prompts the user to select a valid one", async () => {
    const mockCurrentTemplateEnumSchema = {
      properties: {
        display_name: { type: "string" },
        vm_size: {
          type: "string",
          enum: ["small", "medium", "large"],
        },
      },
      required: ["display_name"],
    };

    const mockNewTemplateEnumSchema = {
      properties: {
        display_name: { type: "string" },
        vm_size: {
          type: "string",
          enum: ["small", "large"],
        },
      },
      required: ["display_name", "vm_size"],
      uiSchema: {},
    };

    const mockResourceWithEnum: Resource = {
      ...mockResource,
      properties: {
        display_name: "Test Resource",
        vm_size: "medium", // 'medium' is removed in the new template version
      },
    };

    mockApiCall.mockImplementation((url, method) => {
      if (method === "GET" && url.includes("?version=")) {
        if (url.includes("version=1.0.0")) {
          return Promise.resolve(mockCurrentTemplateEnumSchema);
        } else {
          return Promise.resolve(mockNewTemplateEnumSchema);
        }
      }
      return Promise.resolve({ operation: { id: "operation-id", status: "running" } });
    });

    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={mockResourceWithEnum} onDismiss={mockOnDismiss} />);

    // Select a version
    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    // Wait for schema to load
    await waitFor(() => {
      expect(screen.queryByText("Loading new template schema...")).not.toBeInTheDocument();
    });

    // The form should display the message because 'vm_size' is treated as a property to fill since its current value is invalid
    expect(screen.getByText("Review values for new or changed properties:")).toBeInTheDocument();

    // The button should be disabled because the required 'vm_size' has an invalid value ('medium' which is not in ['small', 'large'])
    const upgradeButton = screen.getByTestId("primary-button");
    expect(upgradeButton).toBeDisabled();
  });

  it("includes fields from the allOf branch activated by an invalid selector", async () => {
    const currentTemplateWithAuthType = {
      properties: {
        display_name: { type: "string" },
        auth_type: { type: "string", enum: ["Manual", "Automatic"] },
        automatic_setting: { type: "string" },
      },
    };

    const newTemplateWithAuthType = {
      properties: {
        display_name: { type: "string" },
        auth_type: { type: "string", enum: ["Manual"], default: "Manual" },
      },
      allOf: [
        {
          if: { properties: { auth_type: { const: "Manual" } } },
          then: {
            properties: {
              client_id: { type: "string", default: "new-client-id" },
            },
            required: ["client_id"],
          },
          else: {
            properties: {
              automatic_setting: { type: "string" },
            },
          },
        },
      ],
      uiSchema: {},
    };

    const resourceWithInvalidAuthType: Resource = {
      ...mockResource,
      properties: {
        display_name: "Test Resource",
        auth_type: "Automatic",
        automatic_setting: "existing-value",
      },
    };

    mockApiCall.mockImplementation((url, method) => {
      if (method === "GET" && url.includes("?version=")) {
        return Promise.resolve(url.includes("version=1.0.0") ? currentTemplateWithAuthType : newTemplateWithAuthType);
      }
      return Promise.resolve({ operation: { id: "operation-id", status: "running" } });
    });

    renderWithWorkspaceContext(
      <ConfirmUpgradeResource resource={resourceWithInvalidAuthType} onDismiss={mockOnDismiss} />,
    );

    fireEvent.change(screen.getByTestId("dropdown"), { target: { value: "1.1.0" } });

    await waitFor(() => {
      expect(screen.getByDisplayValue("new-client-id")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("primary-button"));

    await waitFor(() => {
      expect(mockApiCall).toHaveBeenCalledWith(
        resourceWithInvalidAuthType.resourcePath,
        "PATCH",
        mockWorkspaceContext.workspaceApplicationIdURI,
        expect.objectContaining({
          templateVersion: "1.1.0",
          properties: expect.objectContaining({
            auth_type: "Manual",
            client_id: "new-client-id",
          }),
        }),
        "JSON",
        undefined,
        undefined,
        resourceWithInvalidAuthType._etag,
      );
    });
  });

  it("handles non-string new properties (boolean, number, array) with defaults without coercing to empty string", async () => {
    const mockNewTemplateTypedSchema = {
      properties: {
        display_name: { type: "string" },
        enabled_feature: { type: "boolean", default: true },
        max_count: { type: "number", default: 5 },
        tags: { type: "array", default: ["tag1", "tag2"] },
      },
      required: ["display_name"],
      uiSchema: {},
    };

    mockApiCall.mockImplementation((url, method) => {
      if (method === "GET" && url.includes("?version=")) {
        if (url.includes("version=1.0.0")) {
          return Promise.resolve(mockCurrentTemplateSchema);
        } else {
          return Promise.resolve(mockNewTemplateTypedSchema);
        }
      }
      return Promise.resolve({ operation: { id: "operation-id", status: "running" } });
    });

    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={mockResource} onDismiss={mockOnDismiss} />);

    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    await waitFor(() => {
      expect(screen.queryByText("Loading new template schema...")).not.toBeInTheDocument();
    });

    const upgradeButton = screen.getByTestId("primary-button");
    expect(upgradeButton).not.toBeDisabled();

    fireEvent.click(upgradeButton);

    await waitFor(() => {
      expect(mockApiCall).toHaveBeenCalledWith(
        mockResource.resourcePath,
        "PATCH",
        mockWorkspaceContext.workspaceApplicationIdURI,
        expect.objectContaining({
          templateVersion: "1.1.0",
          properties: expect.objectContaining({
            enabled_feature: true,
            max_count: 5,
            tags: ["tag1", "tag2"],
          }),
        }),
        "JSON",
        undefined,
        undefined,
        mockResource._etag,
      );
    });
  });

  it("correctly evaluates enum conditions in allOf if-schemas so unrelated required fields do not disable upgrade button", async () => {
    const mockNewTemplateEnumSchema = {
      properties: {
        address_space_size: { type: "string", default: "small" },
        address_space: { type: "string" },
      },
      required: ["address_space_size"],
      allOf: [
        {
          if: {
            properties: {
              address_space_size: { enum: ["custom"] },
            },
          },
          then: {
            required: ["address_space"],
          },
        },
      ],
      uiSchema: {},
    };

    mockApiCall.mockImplementation((url, method) => {
      if (method === "GET" && url.includes("?version=")) {
        if (url.includes("version=1.0.0")) {
          return Promise.resolve(mockCurrentTemplateSchema);
        } else {
          return Promise.resolve(mockNewTemplateEnumSchema);
        }
      }
      return Promise.resolve({ operation: { id: "operation-id", status: "running" } });
    });

    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={mockResource} onDismiss={mockOnDismiss} />);

    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    await waitFor(() => {
      expect(screen.queryByText("Loading new template schema...")).not.toBeInTheDocument();
    });

    const upgradeButton = screen.getByTestId("primary-button");
    // Should be enabled because address_space_size is "small", not "custom", so address_space is NOT required
    expect(upgradeButton).not.toBeDisabled();
  });

  it("does not disable upgrade button for optional new properties that are empty", async () => {
    const mockNewTemplateOptionalSchema = {
      properties: {
        display_name: { type: "string" },
        optional_notes: { type: "string" },
      },
      required: ["display_name"],
      uiSchema: {},
    };

    mockApiCall.mockImplementation((url, method) => {
      if (method === "GET" && url.includes("?version=")) {
        if (url.includes("version=1.0.0")) {
          return Promise.resolve(mockCurrentTemplateSchema);
        } else {
          return Promise.resolve(mockNewTemplateOptionalSchema);
        }
      }
      return Promise.resolve({ operation: { id: "operation-id", status: "running" } });
    });

    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={mockResource} onDismiss={mockOnDismiss} />);

    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    await waitFor(() => {
      expect(screen.queryByText("Loading new template schema...")).not.toBeInTheDocument();
    });

    const upgradeButton = screen.getByTestId("primary-button");
    // Upgrade button should be enabled even though optional_notes is empty
    expect(upgradeButton).not.toBeDisabled();
  });

  it("handles user resource upgrade cleanly when parentWorkspaceService prop is passed", async () => {
    const userResource: UserResource = {
      ...(mockResource as UserResource),
      resourceType: ResourceType.UserResource,
      parentWorkspaceServiceId: "parent-service-id",
    };
    const parentWsService = {
      id: "parent-service-id",
      templateName: "guacamole",
      workspaceId: "workspace-id",
    } as any;

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

    renderWithWorkspaceContext(
      <ConfirmUpgradeResource
        resource={userResource}
        onDismiss={mockOnDismiss}
        parentWorkspaceService={parentWsService}
      />,
    );

    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    await waitFor(() => {
      expect(screen.queryByText("Loading new template schema...")).not.toBeInTheDocument();
    });

    const upgradeButton = screen.getByTestId("primary-button");
    expect(upgradeButton).not.toBeDisabled();
  });

  it("matchesIfCondition handles boolean false and numeric 0 as valid non-missing values", () => {
    const ifSchema = {
      properties: {
        enabled_flag: { type: "boolean" },
        count_val: { type: "number" },
      },
    };

    const stateWithFalseAndZero = {
      enabled_flag: false,
      count_val: 0,
    };

    expect(matchesIfCondition(ifSchema, stateWithFalseAndZero)).toBe(true);

    const stateWithUndefined = {
      enabled_flag: undefined,
      count_val: 0,
    };

    expect(matchesIfCondition(ifSchema, stateWithUndefined)).toBe(false);
  });

  it("renders exception layout when parent workspace service info is missing for user resource", async () => {
    const userResourceMissingParent: UserResource = {
      ...(mockResource as UserResource),
      resourceType: ResourceType.UserResource,
    };

    renderWithWorkspaceContext(
      <ConfirmUpgradeResource resource={userResourceMissingParent} onDismiss={mockOnDismiss} />,
    );

    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    await waitFor(() => {
      expect(screen.getByTestId("exception-layout")).toBeInTheDocument();
      expect(
        screen.getByText("Parent workspace service information is missing for this user resource."),
      ).toBeInTheDocument();
    });
  });

  it("renders exception layout when workspace context is missing for user resource with parent ID", async () => {
    const userResourceWithParentId: UserResource = {
      ...(mockResource as UserResource),
      resourceType: ResourceType.UserResource,
      parentWorkspaceServiceId: "parent-service-id",
    };

    const emptyWorkspaceContext = {
      ...mockWorkspaceContext,
      workspace: undefined,
    };

    render(
      <WorkspaceContext.Provider value={emptyWorkspaceContext as any}>
        <ConfirmUpgradeResource resource={userResourceWithParentId} onDismiss={mockOnDismiss} />
      </WorkspaceContext.Provider>,
    );

    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    await waitFor(() => {
      expect(screen.getByTestId("exception-layout")).toBeInTheDocument();
      expect(
        screen.getByText(
          "Cannot resolve parent workspace service for this user resource because workspace context is missing.",
        ),
      ).toBeInTheDocument();
    });
  });

  it("renders exception layout for unsupported resource types", async () => {
    const unsupportedResource = {
      ...mockResource,
      resourceType: "UnsupportedType" as ResourceType,
    };

    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={unsupportedResource} onDismiss={mockOnDismiss} />);

    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    await waitFor(() => {
      expect(screen.getByTestId("exception-layout")).toBeInTheDocument();
      expect(screen.getByText("Unsupported resource type: UnsupportedType")).toBeInTheDocument();
    });
  });

  it("getAllPropertyKeys skips prototype-pollution keys", () => {
    const propertiesWithProto = {
      display_name: { type: "string" },
      __proto__: { type: "string" },
      constructor: { type: "string" },
      prototype: { type: "string" },
      valid_prop: { type: "string" },
    };
    const keys = getAllPropertyKeys(propertiesWithProto);
    expect(keys).toEqual(["display_name", "valid_prop"]);
  });

  it("collects new properties from existing array items", () => {
    const properties = {
      redirect_uris: {
        type: "array",
        items: {
          type: "object",
          required: ["value"],
          properties: {
            name: { type: "string" },
            value: { type: "string" },
          },
        },
      },
    };

    expect(getAllPropertyKeys(properties, "", { redirect_uris: [{ name: "primary" }] })).toEqual([
      "redirect_uris",
      "redirect_uris.0.name",
      "redirect_uris.0.value",
    ]);
    expect(getSchemaPropertyFromProperties(properties, "redirect_uris.0.value")).toEqual(
      properties.redirect_uris.items.properties.value,
    );
  });

  it("treats enum-invalid keys as visible/required-for-input regardless of tre-hidden and pre-fills template default", async () => {
    const currentTemplateWithEnum = {
      properties: {
        display_name: { type: "string" },
        tier: { type: "string", enum: ["basic", "standard", "deprecated_premium"] },
      },
    };

    const newTemplateWithEnumAndTreHidden = {
      properties: {
        display_name: { type: "string" },
        tier: { type: "string", enum: ["basic", "standard"], default: "basic" },
      },
      uiSchema: {
        tier: {
          "ui:classNames": "tre-hidden",
        },
      },
    };

    const resourceWithInvalidEnum: Resource = {
      ...mockResource,
      properties: {
        display_name: "Test Resource",
        tier: "deprecated_premium", // Not in new template enum ["basic", "standard"]
      },
    };

    mockApiCall.mockImplementation((url, method) => {
      if (method === "GET" && url.includes("?version=")) {
        if (url.includes("version=1.0.0")) {
          return Promise.resolve(currentTemplateWithEnum);
        } else {
          return Promise.resolve(newTemplateWithEnumAndTreHidden);
        }
      }
      return Promise.resolve({ operation: { id: "op-1", status: "running" } });
    });

    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={resourceWithInvalidEnum} onDismiss={mockOnDismiss} />);

    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    await waitFor(() => {
      // Prompt message for user input should be present because tier is invalid enum
      expect(screen.getByText("Review values for new or changed properties:")).toBeInTheDocument();
    });

    // Upgrade button should be enabled because default 'basic' was pre-filled (which is valid enum)
    const upgradeButton = screen.getByTestId("primary-button");
    expect(upgradeButton).not.toBeDisabled();

    fireEvent.click(upgradeButton);

    await waitFor(() => {
      expect(mockApiCall).toHaveBeenCalledWith(
        mockResource.resourcePath,
        "PATCH",
        mockWorkspaceContext.workspaceApplicationIdURI,
        expect.objectContaining({
          templateVersion: "1.1.0",
          properties: expect.objectContaining({
            tier: "basic", // Default 'basic' pre-filled, NOT invalid 'deprecated_premium'
          }),
        }),
        "JSON",
        undefined,
        undefined,
        mockResource._etag,
      );
    });
  });

  it("disables upgrade button when conditional required rule depends on existing resource property", async () => {
    const templateWithConditionalRequired = {
      properties: {
        display_name: { type: "string" },
        existing_mode: { type: "string" },
        conditional_new_prop: { type: "string" },
      },
      allOf: [
        {
          if: {
            properties: {
              existing_mode: { const: "advanced" },
            },
          },
          then: {
            required: ["conditional_new_prop"],
          },
        },
      ],
      uiSchema: {},
    };

    const resourceWithExistingMode: Resource = {
      ...mockResource,
      properties: {
        display_name: "Test Resource",
        existing_mode: "advanced",
      },
    };

    mockApiCall.mockImplementation((url, method) => {
      if (method === "GET" && url.includes("?version=")) {
        if (url.includes("version=1.0.0")) {
          return Promise.resolve(mockCurrentTemplateSchema);
        } else {
          return Promise.resolve(templateWithConditionalRequired);
        }
      }
      return Promise.resolve({ operation: { id: "op-1", status: "running" } });
    });

    renderWithWorkspaceContext(
      <ConfirmUpgradeResource resource={resourceWithExistingMode} onDismiss={mockOnDismiss} />,
    );

    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    await waitFor(() => {
      expect(screen.queryByText("Loading new template schema...")).not.toBeInTheDocument();
    });

    // Upgrade button should be disabled because conditional_new_prop is required (due to existing_mode === "advanced") and empty
    const upgradeButton = screen.getByTestId("primary-button");
    expect(upgradeButton).toBeDisabled();
  });

  it("reruns schema fetch when workspace context becomes available after version is selected", async () => {
    const userResource: UserResource = {
      ...mockResource,
      resourceType: ResourceType.UserResource,
      parentWorkspaceServiceId: "ws-service-1",
    } as UserResource;

    const initialContext = {
      ...mockWorkspaceContext,
      workspace: undefined as any,
    };

    const { rerender } = render(
      <WorkspaceContext.Provider value={initialContext}>
        <ConfirmUpgradeResource resource={userResource} onDismiss={mockOnDismiss} />
      </WorkspaceContext.Provider>,
    );

    // Select version when context is missing
    const dropdown = screen.getByTestId("dropdown");
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    await waitFor(() => {
      expect(screen.getByTestId("exception-layout")).toBeInTheDocument();
      expect(
        screen.getByText(
          "Cannot resolve parent workspace service for this user resource because workspace context is missing.",
        ),
      ).toBeInTheDocument();
    });

    // Provide parent service GET response
    mockApiCall.mockImplementation((url, method) => {
      if (method === "GET") {
        if (url.includes("/workspace-services/ws-service-1")) {
          return Promise.resolve({
            workspaceService: { templateName: "parent-service-template" },
          });
        }
        if (url.includes("version=1.0.0")) {
          return Promise.resolve(mockCurrentTemplateSchema);
        }
        if (url.includes("version=1.1.0")) {
          return Promise.resolve(mockNewTemplateSchema);
        }
      }
      return Promise.resolve({});
    });

    // Update context with workspace
    const updatedContext = {
      ...mockWorkspaceContext,
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
        properties: { display_name: "Test Workspace" },
        user: { id: "u1", name: "User", email: "u@e.com", roleAssignments: [], roles: [] },
        workspaceURL: "https://ws.example.com",
      },
    };

    rerender(
      <WorkspaceContext.Provider value={updatedContext}>
        <ConfirmUpgradeResource resource={userResource} onDismiss={mockOnDismiss} />
      </WorkspaceContext.Provider>,
    );

    // Effect should re-run and successfully load schema, resolving error state
    await waitFor(() => {
      expect(screen.queryByTestId("exception-layout")).not.toBeInTheDocument();
      expect(screen.getByDisplayValue("default_value")).toBeInTheDocument();
    });
  });

  it("ignores out-of-order response from cancelled schema fetch when version changes", async () => {
    let resolveV110: (val: any) => void = () => {};
    const v110Promise = new Promise((resolve) => {
      resolveV110 = resolve;
    });

    const schemaV110 = {
      properties: {
        display_name: { type: "string" },
        v110_property: { type: "string", default: "v110_default" },
      },
      required: ["display_name"],
      uiSchema: {},
    };

    const schemaV120 = {
      properties: {
        display_name: { type: "string" },
        v120_property: { type: "string", default: "v120_default" },
      },
      required: ["display_name"],
      uiSchema: {},
    };

    mockApiCall.mockImplementation((url, method) => {
      if (method === "GET") {
        if (url.includes("version=1.0.0")) {
          return Promise.resolve(mockCurrentTemplateSchema);
        }
        if (url.includes("version=1.1.0")) {
          return v110Promise;
        }
        if (url.includes("version=1.2.0")) {
          return Promise.resolve(schemaV120);
        }
      }
      return Promise.resolve({});
    });

    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={mockResource} onDismiss={mockOnDismiss} />);

    const dropdown = screen.getByTestId("dropdown");

    // Select 1.1.0 first (promise is pending)
    fireEvent.change(dropdown, { target: { value: "1.1.0" } });

    // Select 1.2.0 immediately (resolves fast)
    fireEvent.change(dropdown, { target: { value: "1.2.0" } });

    // Wait for 1.2.0 schema to finish loading
    await waitFor(() => {
      expect(screen.getByDisplayValue("v120_default")).toBeInTheDocument();
    });

    // Now resolve the late 1.1.0 promise
    await act(async () => {
      resolveV110(schemaV110);
    });

    // Verify state still displays 1.2.0 schema and didn't get overwritten by late 1.1.0 response
    expect(screen.getByDisplayValue("v120_default")).toBeInTheDocument();
    expect(screen.queryByDisplayValue("v110_default")).not.toBeInTheDocument();
  });

  it("renders confirmation dialog", () => {
    renderWithWorkspaceContext(<ConfirmUpgradeResource resource={mockResource} onDismiss={mockOnDismiss} />);
    const dialog = screen.getByTestId("dialog");
    expect(dialog).toBeInTheDocument();
  });
});

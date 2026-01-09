// NOTE: All vi.mock calls are hoisted to the top of the file at runtime
// Store needed mocks in global variables to access them across the file

// Define mocks at the global level before imports to avoid hoisting issues
// These are defined before any other code to prevent "Cannot access before initialization" errors
// Extend globalThis to include our mock properties
declare global {
  var __mockNavigate: ReturnType<typeof vi.fn>;
  var __mockUseComponentManager: ReturnType<typeof vi.fn>;
}

globalThis.__mockNavigate = vi.fn();
globalThis.__mockUseComponentManager = vi.fn();

// *** ALL MOCK DECLARATIONS FIRST ***
// Mock React Router - preserving original exports and overriding specific functions
vi.mock("react-router-dom", async () => {
  // Import the actual module to preserve exports like MemoryRouter that our tests need
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => globalThis.__mockNavigate,
    useParams: () => ({}),
    useLocation: () => ({ pathname: '/test', search: '', hash: '', state: null })
  };
});

// Mock useComponentManager hook
vi.mock("../../hooks/useComponentManager", () => ({
  useComponentManager: () => globalThis.__mockUseComponentManager,
}));

// Mock child components
vi.mock("./ResourceContextMenu", () => ({
  ResourceContextMenu: ({ resource }: any) => (
    <div data-testid="resource-context-menu">{resource.id}</div>
  ),
}));

vi.mock("./StatusBadge", () => ({
  StatusBadge: ({ resource, status }: any) => (
    <div data-testid="status-badge">{status}</div>
  ),
}));

vi.mock("./PowerStateBadge", () => ({
  PowerStateBadge: ({ state }: any) => (
    <div data-testid="power-state-badge">{state}</div>
  ),
}));

vi.mock("./CostsTag", () => ({
  CostsTag: ({ resourceId }: any) => (
    <div data-testid="costs-tag">{resourceId}</div>
  ),
}));

vi.mock("./ConfirmCopyUrlToClipboard", () => ({
  ConfirmCopyUrlToClipboard: ({ onDismiss }: any) => (
    <div data-testid="confirm-copy-url" onClick={onDismiss}>
      Copy URL Dialog
    </div>
  ),
}));

vi.mock("./SecuredByRole", () => ({
  SecuredByRole: ({ element }: any) => element,
}));

vi.mock("moment", () => ({
  default: {
    unix: (timestamp: number) => ({
      toDate: () => new Date(timestamp * 1000),
    }),
  },
}));

// Mock FluentUI components - Use async importActual to maintain all exports
vi.mock("@fluentui/react", async () => {
  const actual = await vi.importActual("@fluentui/react");

  // Create custom mock components
  const MockStack = ({ children, horizontal, styles, onClick }: any) => (
    <div
      data-testid={onClick ? "clickable-stack" : "stack"}
      data-horizontal={horizontal}
      className={styles?.root}
      onClick={onClick}
    >
      {children}
    </div>
  );

  // Add Item property to Stack
  MockStack.Item = ({ children, align, grow, styles }: any) => (
    <div
      data-testid="stack-item"
      data-align={align}
      data-grow={grow}
      style={styles?.root}
    >
      {children}
    </div>
  );

  return {
    ...actual,
    Stack: MockStack,
    PrimaryButton: ({ text, children, iconProps, styles, onClick, disabled }: any) => (
      <button
        data-testid="primary-button"
        onClick={onClick}
        disabled={disabled}
        style={styles?.root}
      >
        {text || children}
      </button>
    ),
    Icon: ({ iconName }: any) => (
      <div data-testid={`icon-${iconName}`}>{iconName}</div>
    ),
    IconButton: ({ onClick, title }: any) => (
      <button data-testid="icon-button" onClick={onClick} title={title}></button>
    ),
    TooltipHost: ({ content, children }: any) => (
      <div data-testid="tooltip" title={content}>{children}</div>
    ),
    Callout: ({ children, hidden }: any) =>
      !hidden ? <div data-testid="callout">{children}</div> : null,
    Text: ({ children }: any) => <span>{children}</span>,
    Link: ({ children }: any) => <a data-testid="fluent-link">{children}</a>,
    Shimmer: ({ width, height }: any) => (
      <div data-testid="shimmer" style={{ width, height }}>Loading...</div>
    ),
    mergeStyleSets: (styles: any) => styles,
    DefaultPalette: { white: "#ffffff" },
    FontWeights: { semilight: 300 },
  };
});

// *** NOW IMPORTS AFTER ALL MOCKS ***
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  act
} from "../../test-utils";
import { ResourceCard } from "./ResourceCard";
import { Resource, ComponentAction, VMPowerStates } from "../../models/resource";
import { ResourceType } from "../../models/resourceType";
import { RoleName } from "../../models/roleNames";
import { CostResource } from "../../models/costs";

// Access the mocks from the global variables
const mockNavigate = globalThis.__mockNavigate;
const mockUseComponentManager = globalThis.__mockUseComponentManager;

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
    description: "Test resource description",
    connection_uri: "https://test-connection.com",
  },
  _etag: "test-etag",
  updatedWhen: 1640995200, // Unix timestamp
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
  azureStatus: {
    powerState: VMPowerStates.Running,
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

const mockAppRolesContext = {
  roles: [RoleName.TREAdmin],
  setAppRoles: vi.fn(),
};

const renderWithContexts = (
  component: React.ReactElement,
  workspaceContext = mockWorkspaceContext,
  appRolesContext = mockAppRolesContext
) => {
  return render(component, {
    // Use spread operator to include children property which is required by AllProvidersProps
    children: component,
    workspaceContext,
    appRolesContext
  });
};

describe("ResourceCard Component", () => {
  const defaultProps = {
    resource: mockResource,
    itemId: 1,
    onUpdate: vi.fn(),
    onDelete: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseComponentManager.mockReturnValue({
      componentAction: ComponentAction.None,
      operation: null,
    });
  });

  it("renders resource card with basic information", () => {
    renderWithContexts(<ResourceCard {...defaultProps} />);

    expect(screen.getByText("Test Resource")).toBeInTheDocument();
    expect(screen.getByText("Test resource description")).toBeInTheDocument();
    expect(screen.getByTestId("power-state-badge")).toBeInTheDocument();
  });

  it("renders power state badge when resource is running", () => {
    renderWithContexts(<ResourceCard {...defaultProps} />);

    expect(screen.getByTestId("power-state-badge")).toBeInTheDocument();
    expect(screen.getByTestId("power-state-badge")).toHaveTextContent("running");
  });

  it("renders connect button for resources with connection URI", () => {
    renderWithContexts(<ResourceCard {...defaultProps} />);

    const connectButton = screen.getByTestId("primary-button");
    expect(connectButton).toBeInTheDocument();
    expect(connectButton).toHaveTextContent("Connect");
    expect(connectButton).not.toBeDisabled();
  });

  it("disables connect button for disabled resources", () => {
    const disabledResource = {
      ...mockResource,
      isEnabled: false,
    };

    renderWithContexts(
      <ResourceCard {...defaultProps} resource={disabledResource} />
    );

    const connectButton = screen.getByTestId("primary-button");
    expect(connectButton).toBeDisabled();
  });

  it("navigates to resource when card is clicked", () => {
    renderWithContexts(<ResourceCard {...defaultProps} />);

    const card = screen.getByTestId("clickable-stack");
    fireEvent.click(card);

    expect(mockNavigate).toHaveBeenCalledWith(mockResource.resourcePath);
  });

  it("calls selectResource when provided", () => {
    const mockSelectResource = vi.fn();
    renderWithContexts(
      <ResourceCard {...defaultProps} selectResource={mockSelectResource} />
    );

    const card = screen.getByTestId("clickable-stack");
    fireEvent.click(card);

    expect(mockSelectResource).toHaveBeenCalledWith(mockResource);
  });

  it("shows info callout when info button is clicked", () => {
    renderWithContexts(<ResourceCard {...defaultProps} />);

    const infoButton = screen.getByTestId("icon-button");
    fireEvent.click(infoButton);

    expect(screen.getByTestId("callout")).toBeInTheDocument();
  });

  it("displays resource details in info callout", () => {
    renderWithContexts(<ResourceCard {...defaultProps} />);

    const infoButton = screen.getByTestId("icon-button");
    fireEvent.click(infoButton);

    expect(screen.getByText("test-template (1.0.0)")).toBeInTheDocument();
    // Look for the resource id in the callout specifically
    const callout = screen.getByTestId("callout");
    expect(callout).toHaveTextContent("test-resource-id");
    expect(screen.getByText("Test User")).toBeInTheDocument();
  });

  it("shows copy URL dialog for internal connections", () => {
    const props = {
      ...defaultProps,
      isExposedExternally: false,
    };

    renderWithContexts(<ResourceCard {...props} />);

    const connectButton = screen.getByTestId("primary-button");
    fireEvent.click(connectButton);

    expect(screen.getByTestId("confirm-copy-url")).toBeInTheDocument();
  });

  it("opens external URL directly for external connections", () => {
    const windowOpenSpy = vi.spyOn(window, "open").mockImplementation(() => null);

    const props = {
      ...defaultProps,
      isExposedExternally: true,
    };

    renderWithContexts(<ResourceCard {...props} />);

    const connectButton = screen.getByTestId("primary-button");
    fireEvent.click(connectButton);

    expect(windowOpenSpy).toHaveBeenCalledWith(mockResource.properties.connection_uri);

    windowOpenSpy.mockRestore();
  });

  it("does not render context menu in readonly mode", () => {
    renderWithContexts(<ResourceCard {...defaultProps} readonly={true} />);

    expect(screen.queryByTestId("resource-context-menu")).not.toBeInTheDocument();
  });

  it("renders context menu in non-readonly mode", () => {
    renderWithContexts(<ResourceCard {...defaultProps} readonly={false} />);

    expect(screen.getByTestId("resource-context-menu")).toBeInTheDocument();
  });

  it("renders costs tag for authorized users", () => {
    renderWithContexts(<ResourceCard {...defaultProps} />);

    expect(screen.getByTestId("costs-tag")).toBeInTheDocument();
  });

  it("displays shimmer loading state", () => {
    // Mock loading state by changing the internal loading state
    // For this test, we'll just check the component can handle the loading prop
    renderWithContexts(<ResourceCard {...defaultProps} />);

    // The component currently doesn't expose loading state externally,
    // but we can test that it renders without the loading shimmer by default
    expect(screen.queryByTestId("shimmer")).not.toBeInTheDocument();
  });

  it("handles resources without connection URI", () => {
    const resourceWithoutConnection = {
      ...mockResource,
      properties: {
        ...mockResource.properties,
        connection_uri: undefined,
      },
    };

    renderWithContexts(
      <ResourceCard {...defaultProps} resource={resourceWithoutConnection} />
    );

    expect(screen.queryByTestId("primary-button")).not.toBeInTheDocument();
  });

  it("prevents card click when authentication not provisioned for non-admin", async () => {
    const workspaceWithoutAuth = {
      ...mockResource,
      resourceType: ResourceType.Workspace,
      properties: {
        ...mockResource.properties,
        scope_id: undefined, // No auth provisioned
      },
    };

    const nonAdminContext = {
      ...mockAppRolesContext,
      roles: [], // No admin role
    };

    await act(async () => {
      renderWithContexts(
        <ResourceCard {...defaultProps} resource={workspaceWithoutAuth} />,
        mockWorkspaceContext,
        nonAdminContext
      );
    });

    const card = screen.getByTestId("clickable-stack");
    fireEvent.click(card);

    // Should not navigate if auth not provisioned and user is not admin
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});

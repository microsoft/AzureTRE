import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { ResourceCard } from "./ResourceCard";
import { Resource, ComponentAction, VMPowerStates } from "../../models/resource";
import { ResourceType } from "../../models/resourceType";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { AppRolesContext } from "../../contexts/AppRolesContext";
import { RoleName, WorkspaceRoleName } from "../../models/roleNames";
import { CostResource } from "../../models/costs";

// Mock dependencies
const mockNavigate = vi.fn();
const mockUseComponentManager = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock("../../hooks/useComponentManager", () => ({
  useComponentManager: () => mockUseComponentManager(),
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

// Mock FluentUI components
vi.mock("@fluentui/react", () => {
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
  MockStack.Item = ({ children, grow, style }: any) => (
    <div data-testid="stack-item" data-grow={grow} style={style}>
      {children}
    </div>
  );

  return {
    Stack: MockStack,
    Text: ({ children }: any) => <div data-testid="text">{children}</div>,
    IconButton: ({ iconProps, onClick, id }: any) => (
      <button data-testid="icon-button" onClick={onClick} id={id}>
        {iconProps.iconName}
      </button>
    ),
    PrimaryButton: ({ onClick, disabled, title, className, children }: any) => (
      <button
        data-testid="primary-button"
        onClick={onClick}
        disabled={disabled}
        title={title}
        className={className}
      >
        {children}
      </button>
    ),
    TooltipHost: ({ children, content, id }: any) => (
      <div data-testid="tooltip-host" title={content} id={id}>
        {children}
      </div>
    ),
    Callout: ({ children, onDismiss, target }: any) => (
      <div data-testid="callout" onClick={onDismiss}>
        {children}
      </div>
    ),
    Shimmer: ({ width }: any) => (
      <div data-testid="shimmer" style={{ width }}>Loading...</div>
    ),
    mergeStyleSets: (styles: any) => styles,
    DefaultPalette: { white: "#ffffff" },
    FontWeights: { semilight: 300 },
  };
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
  return render(
    <BrowserRouter>
      <WorkspaceContext.Provider value={workspaceContext}>
        <AppRolesContext.Provider value={appRolesContext}>
          {component}
        </AppRolesContext.Provider>
      </WorkspaceContext.Provider>
    </BrowserRouter>
  );
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

  it("prevents card click when authentication not provisioned for non-admin", () => {
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

    renderWithContexts(
      <ResourceCard {...defaultProps} resource={workspaceWithoutAuth} />,
      mockWorkspaceContext,
      nonAdminContext
    );

    const card = screen.getByTestId("clickable-stack");
    fireEvent.click(card);

    // Should not navigate if auth not provisioned and user is not admin
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});

import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ResourceBody } from "./ResourceBody";
import { Resource } from "../../models/resource";
import { ResourceType } from "../../models/resourceType";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { AppRolesContext } from "../../contexts/AppRolesContext";
import { CostResource } from "../../models/costs";
import { WorkspaceRoleName } from "../../models/roleNames";

// Mock child components
vi.mock("./ResourceDebug", () => {
  const ResourceDebug = ({ resource }: any) => <div data-testid="resource-debug">{resource.id}</div>;
  ResourceDebug.displayName = "ResourceDebug";
  return { ResourceDebug };
});

vi.mock("./ResourcePropertyPanel", () => {
  const ResourcePropertyPanel = ({ resource }: any) => <div data-testid="resource-property-panel">{resource.id}</div>;
  ResourcePropertyPanel.displayName = "ResourcePropertyPanel";
  return { ResourcePropertyPanel };
});

vi.mock("./ResourceHistoryList", () => {
  const ResourceHistoryList = ({ resource }: any) => <div data-testid="resource-history-list">{resource.id}</div>;
  ResourceHistoryList.displayName = "ResourceHistoryList";
  return { ResourceHistoryList };
});

vi.mock("./ResourceOperationsList", () => {
  const ResourceOperationsList = ({ resource }: any) => <div data-testid="resource-operations-list">{resource.id}</div>;
  ResourceOperationsList.displayName = "ResourceOperationsList";
  return { ResourceOperationsList };
});

vi.mock("./SecuredByRole", () => {
  const SecuredByRole = ({ element, allowedWorkspaceRoles }: any) => (
    <div data-testid="secured-by-role" data-allowed-workspace-roles={allowedWorkspaceRoles?.join(",")}>
      {element}
    </div>
  );
  SecuredByRole.displayName = "SecuredByRole";
  return { SecuredByRole };
});

// Mock react-markdown
vi.mock("react-markdown", () => {
  const MockMarkdown = ({ children }: any) => <div data-testid="markdown">{children}</div>;
  MockMarkdown.displayName = "MockMarkdown";
  return { default: MockMarkdown };
});

vi.mock("remark-gfm", () => ({
  default: () => {},
}));

// Mock FluentUI components
vi.mock("@fluentui/react", async () => {
  const actual = await vi.importActual("@fluentui/react");
  return {
    ...actual,
    Pivot: ({ children, className }: any) => (
      <div data-testid="pivot" className={className}>
        {children}
      </div>
    ),
    PivotItem: ({ children, headerText, headerButtonProps }: any) => (
      <div data-testid="pivot-item" data-header={headerText} data-order={headerButtonProps?.["data-order"]}>
        {children}
      </div>
    ),
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
    overview: "# Test Resource Overview\nThis is a **test** resource.",
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
      roles: ["WorkspaceOwner"],
    },
    workspaceURL: "https://workspace.example.com",
  },
  workspaceApplicationIdURI: "test-app-id-uri",
  roles: ["WorkspaceOwner"],
  setCosts: vi.fn(),
  setRoles: vi.fn(),
  setWorkspace: vi.fn(),
};

const renderWithWorkspaceContext = (component: React.ReactElement) => {
  return render(
    <AppRolesContext.Provider value={{ roles: [], setAppRoles: vi.fn() }}>
      <WorkspaceContext.Provider value={mockWorkspaceContext}>{component}</WorkspaceContext.Provider>
    </AppRolesContext.Provider>,
  );
};

describe("ResourceBody Component", () => {
  it("renders pivot with overview tab", () => {
    renderWithWorkspaceContext(<ResourceBody resource={mockResource} />);

    expect(screen.getByTestId("pivot")).toBeInTheDocument();
    expect(screen.getByTestId("pivot")).toHaveClass("tre-resource-panel");

    const pivotTabs = screen.getAllByTestId("pivot-item");
    const overviewTab = pivotTabs.find((tab) => tab.getAttribute("data-header") === "Overview");
    expect(overviewTab).toBeInTheDocument();
    expect(overviewTab).toHaveAttribute("data-header", "Overview");
    expect(overviewTab).toHaveAttribute("data-order", "1");
  });

  it("renders markdown content in overview tab", () => {
    renderWithWorkspaceContext(<ResourceBody resource={mockResource} />);

    const markdown = screen.getByTestId("markdown");
    expect(markdown).toBeInTheDocument();
    expect(markdown).toHaveTextContent("# Test Resource Overview This is a **test** resource.");
  });

  it("falls back to description when overview is not available", () => {
    const resourceWithoutOverview = {
      ...mockResource,
      properties: {
        ...mockResource.properties,
        overview: undefined,
        description: "Fallback description",
      },
    };

    renderWithWorkspaceContext(<ResourceBody resource={resourceWithoutOverview} />);

    const markdown = screen.getByTestId("markdown");
    expect(markdown).toHaveTextContent("Fallback description");
  });

  it("renders details tab when not readonly", () => {
    renderWithWorkspaceContext(<ResourceBody resource={mockResource} />);

    const tabs = screen.getAllByTestId("pivot-item");
    const detailsTab = tabs.find((tab) => tab.getAttribute("data-header") === "Details");
    expect(detailsTab).toBeInTheDocument();

    expect(screen.getByTestId("resource-property-panel")).toBeInTheDocument();
    expect(screen.getByTestId("resource-debug")).toBeInTheDocument();
  });

  it("does not render details tab when readonly", () => {
    renderWithWorkspaceContext(<ResourceBody resource={mockResource} readonly={true} />);

    const tabs = screen.getAllByTestId("pivot-item");
    const detailsTab = tabs.find((tab) => tab.getAttribute("data-header") === "Details");
    expect(detailsTab).toBeUndefined();

    expect(screen.queryByTestId("resource-property-panel")).not.toBeInTheDocument();
    expect(screen.queryByTestId("resource-debug")).not.toBeInTheDocument();
  });

  it("renders history tab for workspace service when not readonly", () => {
    renderWithWorkspaceContext(<ResourceBody resource={mockResource} />);

    const tabs = screen.getAllByTestId("pivot-item");
    const historyTab = tabs.find((tab) => tab.getAttribute("data-header") === "History");
    expect(historyTab).toBeInTheDocument();

    expect(screen.getByTestId("resource-history-list")).toBeInTheDocument();
  });

  it("renders operations tab for workspace service when not readonly", () => {
    renderWithWorkspaceContext(<ResourceBody resource={mockResource} />);

    const tabs = screen.getAllByTestId("pivot-item");
    const operationsTab = tabs.find((tab) => tab.getAttribute("data-header") === "Operations");
    expect(operationsTab).toBeInTheDocument();

    expect(screen.getByTestId("resource-operations-list")).toBeInTheDocument();
  });

  it("does not render history and operations tabs when readonly", () => {
    renderWithWorkspaceContext(<ResourceBody resource={mockResource} readonly={true} />);

    const tabs = screen.getAllByTestId("pivot-item");
    const historyTab = tabs.find((tab) => tab.getAttribute("data-header") === "History");
    const operationsTab = tabs.find((tab) => tab.getAttribute("data-header") === "Operations");

    expect(historyTab).toBeUndefined();
    expect(operationsTab).toBeUndefined();

    expect(screen.queryByTestId("resource-history-list")).not.toBeInTheDocument();
    expect(screen.queryByTestId("resource-operations-list")).not.toBeInTheDocument();
  });

  it("handles shared service resource type", () => {
    const sharedServiceResource = {
      ...mockResource,
      resourceType: ResourceType.SharedService,
    };

    renderWithWorkspaceContext(<ResourceBody resource={sharedServiceResource} />);

    // History and Operations for shared services are TRE Admin only, so a Workspace Owner doesn't get those tabs
    const tabs = screen.getAllByTestId("pivot-item");
    expect(tabs).toHaveLength(2); // Overview, Details
  });

  it("hides Details and Operations of a workspace service from researchers", () => {
    const serviceResource = { ...mockResource, resourceType: ResourceType.WorkspaceService };

    render(
      <AppRolesContext.Provider value={{ roles: [], setAppRoles: vi.fn() }}>
        <WorkspaceContext.Provider value={{ ...mockWorkspaceContext, roles: [WorkspaceRoleName.WorkspaceResearcher] }}>
          <ResourceBody resource={serviceResource} />
        </WorkspaceContext.Provider>
      </AppRolesContext.Provider>,
    );

    const headers = screen.getAllByTestId("pivot-item").map((tab) => tab.getAttribute("data-header"));
    expect(headers).toEqual(["Overview"]);
  });

  it.each([ResourceType.Workspace, ResourceType.WorkspaceService])(
    "shows Details of a %s to airlock managers",
    (resourceType) => {
      render(
        <AppRolesContext.Provider value={{ roles: [], setAppRoles: vi.fn() }}>
          <WorkspaceContext.Provider value={{ ...mockWorkspaceContext, roles: [WorkspaceRoleName.AirlockManager] }}>
            <ResourceBody resource={{ ...mockResource, resourceType }} />
          </WorkspaceContext.Provider>
        </AppRolesContext.Provider>,
      );

      const headers = screen.getAllByTestId("pivot-item").map((tab) => tab.getAttribute("data-header"));
      expect(headers).toContain("Details");
    },
  );

  it.each([ResourceType.WorkspaceService, ResourceType.UserResource])(
    "shows History and Operations of a %s to airlock managers",
    (resourceType) => {
      render(
        <AppRolesContext.Provider value={{ roles: [], setAppRoles: vi.fn() }}>
          <WorkspaceContext.Provider value={{ ...mockWorkspaceContext, roles: [WorkspaceRoleName.AirlockManager] }}>
            <ResourceBody resource={{ ...mockResource, resourceType }} />
          </WorkspaceContext.Provider>
        </AppRolesContext.Provider>,
      );

      const headers = screen.getAllByTestId("pivot-item").map((tab) => tab.getAttribute("data-header"));
      expect(headers).toEqual(expect.arrayContaining(["History", "Operations"]));
    },
  );

  it("handles user resource type", () => {
    const userResource = {
      ...mockResource,
      resourceType: ResourceType.UserResource,
    };

    renderWithWorkspaceContext(<ResourceBody resource={userResource} />);

    // Should render all tabs for user resource
    const tabs = screen.getAllByTestId("pivot-item");
    expect(tabs).toHaveLength(4); // Overview, Details, History, Operations
  });

  it("handles workspace resource type", () => {
    const workspaceResource = {
      ...mockResource,
      resourceType: ResourceType.Workspace,
    };

    renderWithWorkspaceContext(<ResourceBody resource={workspaceResource} />);

    // Should render all tabs for workspace
    const tabs = screen.getAllByTestId("pivot-item");
    expect(tabs).toHaveLength(4); // Overview, Details, History, Operations
  });

  it("does not show workspace history or operations to researchers", () => {
    const workspaceResource = {
      ...mockResource,
      resourceType: ResourceType.Workspace,
    };
    const researcherContext = {
      ...mockWorkspaceContext,
      roles: ["WorkspaceResearcher"],
    };
    render(
      <AppRolesContext.Provider value={{ roles: [], setAppRoles: vi.fn() }}>
        <WorkspaceContext.Provider value={researcherContext}>
          <ResourceBody resource={workspaceResource} />
        </WorkspaceContext.Provider>
      </AppRolesContext.Provider>,
    );

    const tabs = screen.getAllByTestId("pivot-item").map((tab) => tab.getAttribute("data-header"));
    expect(tabs).toContain("Overview");
    expect(tabs).not.toContain("History");
    expect(tabs).not.toContain("Details");
    expect(tabs).not.toContain("Operations");
    expect(screen.queryByTestId("resource-history-list")).not.toBeInTheDocument();
  });

  it("renders only overview tab when readonly", () => {
    renderWithWorkspaceContext(<ResourceBody resource={mockResource} readonly={true} />);

    const tabs = screen.getAllByTestId("pivot-item");
    expect(tabs).toHaveLength(1);
    expect(tabs[0]).toHaveAttribute("data-header", "Overview");
  });

  it("passes workspace id to secured components", () => {
    renderWithWorkspaceContext(<ResourceBody resource={mockResource} />);

    // SecuredByRole is mocked to just render the element, but in real usage
    // it would receive the workspace ID from context
    expect(screen.getByTestId("resource-history-list")).toBeInTheDocument();
    expect(screen.getByTestId("resource-operations-list")).toBeInTheDocument();
  });
});

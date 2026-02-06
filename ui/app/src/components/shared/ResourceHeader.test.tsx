import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ResourceHeader } from "./ResourceHeader";
import { Resource, ComponentAction, VMPowerStates } from "../../models/resource";
import { ResourceType } from "../../models/resourceType";

// Mock child components
vi.mock("./ResourceContextMenu", () => {
    const ResourceContextMenu = ({ resource, commandBar, componentAction }: any) => (
        <div data-testid="resource-context-menu">
            <div>Resource: {resource.id}</div>
            <div>CommandBar: {commandBar?.toString()}</div>
            <div>Action: {componentAction}</div>
        </div>
    );
    ResourceContextMenu.displayName = 'ResourceContextMenu';
    return { ResourceContextMenu };
});

vi.mock("./StatusBadge", () => {
    const StatusBadge = ({ resource, status }: any) => (
        <div data-testid="status-badge">
            <div>Resource: {resource.id}</div>
            <div>Status: {status}</div>
        </div>
    );
    StatusBadge.displayName = 'StatusBadge';
    return { StatusBadge };
});

vi.mock("./PowerStateBadge", () => {
    const PowerStateBadge = ({ state }: any) => (
        <div data-testid="power-state-badge">Power: {state}</div>
    );
    PowerStateBadge.displayName = 'PowerStateBadge';
    return { PowerStateBadge };
});

// Mock FluentUI components
vi.mock("@fluentui/react", () => {
    const MockStack = ({ children, horizontal }: any) => (
        <div data-testid="stack" data-horizontal={horizontal}>
            {children}
        </div>
    );
    const Item = ({ children, style, align, grow }: any) => (
        <div data-testid="stack-item" style={style} data-align={align} data-grow={grow}>
            {children}
        </div>
    );
    Item.displayName = 'StackItem';
    MockStack.Item = Item;

    return {
        Stack: MockStack,
        ProgressIndicator: ({ description }: any) => (
            <div data-testid="progress-indicator">{description}</div>
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
    azureStatus: {
        powerState: VMPowerStates.Running,
    },
};

const mockLatestUpdate = {
    componentAction: ComponentAction.None,
    operation: {
        id: "test-operation-id",
        resourceId: "test-resource-id",
        resourcePath: "/test/path",
        resourceVersion: 1,
        status: "deployed",
        action: "install",
        message: "Test message",
        createdWhen: Date.now(),
        updatedWhen: Date.now(),
        user: {
            id: "test-user-id",
            name: "Test User",
            email: "test@example.com",
            roleAssignments: [],
            roles: ["workspace_researcher"],
        },
    },
};

describe("ResourceHeader Component", () => {
    it("renders resource display name", () => {
        render(
            <ResourceHeader
                resource={mockResource}
                latestUpdate={mockLatestUpdate}
            />
        );

        expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Test Resource");
    });

    it("renders power state badge when available", () => {
        render(
            <ResourceHeader
                resource={mockResource}
                latestUpdate={mockLatestUpdate}
            />
        );

        expect(screen.getByTestId("power-state-badge")).toBeInTheDocument();
        const powerBadge = screen.getByTestId("power-state-badge");
        expect(powerBadge).toHaveTextContent("Power: VM running");
    });

    it("does not render power state badge when not available", () => {
        const resourceWithoutPowerState = {
            ...mockResource,
            azureStatus: undefined,
        };

        render(
            <ResourceHeader
                resource={resourceWithoutPowerState}
                latestUpdate={mockLatestUpdate}
            />
        );

        expect(screen.queryByTestId("power-state-badge")).not.toBeInTheDocument();
    });

    it("renders status badge with deployment status", () => {
        render(
            <ResourceHeader
                resource={mockResource}
                latestUpdate={mockLatestUpdate}
            />
        );

        expect(screen.getByTestId("status-badge")).toBeInTheDocument();
        expect(screen.getByText("Status: deployed")).toBeInTheDocument();
    });

    it("renders status badge with operation status when available", () => {
        const latestUpdateWithOperation = {
            componentAction: ComponentAction.None,
            operation: {
                id: "operation-id",
                resourceId: "test-resource-id",
                resourcePath: "/test/path",
                resourceVersion: 1,
                status: "running",
                action: "deploy",
                message: "Test message",
                createdWhen: Date.now(),
                updatedWhen: Date.now(),
                user: {
                    id: "test-user-id",
                    name: "Test User",
                    email: "test@example.com",
                    roleAssignments: [],
                    roles: ["workspace_researcher"],
                },
            },
        };

        render(
            <ResourceHeader
                resource={mockResource}
                latestUpdate={latestUpdateWithOperation}
            />
        );

        expect(screen.getByText("Status: running")).toBeInTheDocument();
    });

    it("renders context menu when not readonly", () => {
        render(
            <ResourceHeader
                resource={mockResource}
                latestUpdate={mockLatestUpdate}
            />
        );

        expect(screen.getByTestId("resource-context-menu")).toBeInTheDocument();
        expect(screen.getByText("CommandBar: true")).toBeInTheDocument();
    });

    it("does not render context menu when readonly", () => {
        render(
            <ResourceHeader
                resource={mockResource}
                latestUpdate={mockLatestUpdate}
                readonly={true}
            />
        );

        expect(screen.queryByTestId("resource-context-menu")).not.toBeInTheDocument();
    });

    it("renders progress indicator when resource is locked", () => {
        const lockedUpdate = {
            componentAction: ComponentAction.Lock,
            operation: {
                id: "operation-id",
                resourceId: "test-resource-id",
                resourcePath: "/test/path",
                resourceVersion: 1,
                status: "running",
                action: "deploy",
                message: "Test message",
                createdWhen: Date.now(),
                updatedWhen: Date.now(),
                user: {
                    id: "test-user-id",
                    name: "Test User",
                    email: "test@example.com",
                    roleAssignments: [],
                    roles: ["workspace_researcher"],
                },
            },
        };

        render(
            <ResourceHeader
                resource={mockResource}
                latestUpdate={lockedUpdate}
            />
        );

        expect(screen.getByTestId("progress-indicator")).toBeInTheDocument();
        expect(screen.getByText("Resource locked while it updates")).toBeInTheDocument();
    });

    it("does not render progress indicator when resource is not locked", () => {
        render(
            <ResourceHeader
                resource={mockResource}
                latestUpdate={mockLatestUpdate}
            />
        );

        expect(screen.queryByTestId("progress-indicator")).not.toBeInTheDocument();
    });

    it("applies border styling when not readonly", () => {
        render(
            <ResourceHeader
                resource={mockResource}
                latestUpdate={mockLatestUpdate}
            />
        );

        const stackItems = screen.getAllByTestId("stack-item");
        const headerItem = stackItems[0];
        expect(headerItem).toHaveStyle({ borderBottom: "1px #999 solid" });
    });

    it("does not apply border styling when readonly", () => {
        render(
            <ResourceHeader
                resource={mockResource}
                latestUpdate={mockLatestUpdate}
                readonly={true}
            />
        );

        const stackItems = screen.getAllByTestId("stack-item");
        const headerItem = stackItems[0];
        expect(headerItem).not.toHaveStyle({ borderBottom: "1px #999 solid" });
    });

    it("passes component action to context menu", () => {
        const updateWithAction = {
            componentAction: ComponentAction.Reload,
            operation: {
                id: "operation-id",
                resourceId: "test-resource-id",
                resourcePath: "/test/path",
                resourceVersion: 1,
                status: "running",
                action: "deploy",
                message: "Test message",
                createdWhen: Date.now(),
                updatedWhen: Date.now(),
                user: {
                    id: "test-user-id",
                    name: "Test User",
                    email: "test@example.com",
                    roleAssignments: [],
                    roles: ["workspace_researcher"],
                },
            },
        };

        render(
            <ResourceHeader
                resource={mockResource}
                latestUpdate={updateWithAction}
            />
        );

        expect(screen.getByText("Action: 1")).toBeInTheDocument(); // ComponentAction.Reload = 1
    });

    it("renders nothing when resource has no id", () => {
        const resourceWithoutId = {
            ...mockResource,
            id: "",
        };

        const { container } = render(
            <ResourceHeader
                resource={resourceWithoutId}
                latestUpdate={mockLatestUpdate}
            />
        );

        expect(container.firstChild).toBeNull();
    });

    it("renders with proper layout structure", () => {
        render(
            <ResourceHeader
                resource={mockResource}
                latestUpdate={mockLatestUpdate}
            />
        );

        const stacks = screen.getAllByTestId("stack");
        const stackItems = screen.getAllByTestId("stack-item");

        // Should have nested stack structure
        expect(stacks.length).toBeGreaterThan(1);
        expect(stackItems.length).toBeGreaterThan(2);

        // Main header stack should be horizontal
        const headerStack = stacks.find(stack =>
            stack.getAttribute("data-horizontal") === "true"
        );
        expect(headerStack).toBeInTheDocument();
    });

    it("aligns status badge to center", () => {
        render(
            <ResourceHeader
                resource={mockResource}
                latestUpdate={mockLatestUpdate}
            />
        );

        const stackItems = screen.getAllByTestId("stack-item");
        const statusItem = stackItems.find(item =>
            item.getAttribute("data-align") === "center"
        );
        expect(statusItem).toBeInTheDocument();
    });
});

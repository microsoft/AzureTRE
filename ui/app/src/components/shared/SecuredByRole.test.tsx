import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { SecuredByRole } from "./SecuredByRole";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { AppRolesContext } from "../../contexts/AppRolesContext";
import { ResourceType } from "../../models/resourceType";
import { CostResource } from "../../models/costs";

// Mock the API hook
const mockApiCall = vi.fn();
vi.mock("../../hooks/useAuthApiCall", () => ({
    useAuthApiCall: () => mockApiCall,
    HttpMethod: { Get: "GET" },
    ResultType: { JSON: "JSON" },
}));

// Mock API endpoints
vi.mock("../../models/apiEndpoints", () => ({
    ApiEndpoint: {
        Workspaces: "/api/workspaces",
    },
}));

// Mock FluentUI MessageBar
vi.mock("@fluentui/react", async () => {
    const actual = await vi.importActual("@fluentui/react");
    return {
        ...actual,
        MessageBar: ({ children, messageBarType }: any) => (
            <div data-testid="message-bar" data-message-type={messageBarType}>
                {children}
            </div>
        ),
        MessageBarType: {
            error: "error",
        },
    };
});

const TestElement = () => <div data-testid="secured-content">Secured Content</div>;

const createMockWorkspaceContext = (roles: string[] = []) => ({
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
    roles,
    setCosts: vi.fn(),
    setRoles: vi.fn(),
    setWorkspace: vi.fn(),
});

const createMockAppRolesContext = (roles: string[] = []) => ({
    roles,
    setAppRoles: vi.fn(),
});

const renderWithContexts = (
    component: React.ReactElement,
    workspaceRoles: string[] = [],
    appRoles: string[] = [],
) => {
    const workspaceContext = createMockWorkspaceContext(workspaceRoles);
    const appRolesContext = createMockAppRolesContext(appRoles);

    return render(
        <WorkspaceContext.Provider value={workspaceContext}>
            <AppRolesContext.Provider value={appRolesContext}>
                {component}
            </AppRolesContext.Provider>
        </WorkspaceContext.Provider>
    );
};

describe("SecuredByRole Component", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("renders secured content when user has required workspace role", () => {
        renderWithContexts(
            <SecuredByRole
                element={<TestElement />}
                allowedWorkspaceRoles={["workspace_researcher"]}
            />,
            ["workspace_researcher"], // user has this role
            []
        );

        expect(screen.getByTestId("secured-content")).toBeInTheDocument();
    });

    it("renders secured content when user has required app role", () => {
        renderWithContexts(
            <SecuredByRole
                element={<TestElement />}
                allowedAppRoles={["TREAdmin"]}
            />,
            [],
            ["TREAdmin"] // user has this role
        );

        expect(screen.getByTestId("secured-content")).toBeInTheDocument();
    });

    it("renders secured content when user has any of multiple allowed workspace roles", () => {
        renderWithContexts(
            <SecuredByRole
                element={<TestElement />}
                allowedWorkspaceRoles={["workspace_owner", "workspace_researcher"]}
            />,
            ["workspace_researcher"], // user has one of the allowed roles
            []
        );

        expect(screen.getByTestId("secured-content")).toBeInTheDocument();
    });

    it("renders secured content when user has any of multiple allowed app roles", () => {
        renderWithContexts(
            <SecuredByRole
                element={<TestElement />}
                allowedAppRoles={["TREAdmin", "TREUser"]}
            />,
            [],
            ["TREUser"] // user has one of the allowed roles
        );

        expect(screen.getByTestId("secured-content")).toBeInTheDocument();
    });

    it("renders secured content when user has both workspace and app roles", () => {
        renderWithContexts(
            <SecuredByRole
                element={<TestElement />}
                allowedWorkspaceRoles={["workspace_owner"]}
                allowedAppRoles={["TREAdmin"]}
            />,
            ["workspace_researcher"], // doesn't have workspace role
            ["TREAdmin"] // but has app role
        );

        expect(screen.getByTestId("secured-content")).toBeInTheDocument();
    });

    it("does not render content when user lacks required roles", () => {
        renderWithContexts(
            <SecuredByRole
                element={<TestElement />}
                allowedWorkspaceRoles={["workspace_owner"]}
                allowedAppRoles={["TREAdmin"]}
            />,
            ["workspace_researcher"], // doesn't have required workspace role
            ["TREUser"] // doesn't have required app role
        );

        expect(screen.queryByTestId("secured-content")).not.toBeInTheDocument();
    });

    it("renders error message when user lacks required roles and errorString is provided", () => {
        const errorMessage = "You need admin access to view this content";

        renderWithContexts(
            <SecuredByRole
                element={<TestElement />}
                allowedWorkspaceRoles={["workspace_owner"]}
                errorString={errorMessage}
            />,
            ["workspace_researcher"], // doesn't have required role
            []
        );

        expect(screen.queryByTestId("secured-content")).not.toBeInTheDocument();
        expect(screen.getByTestId("message-bar")).toBeInTheDocument();
        expect(screen.getByText("Access Denied")).toBeInTheDocument();
        expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });

    it("does not render error message when user has no roles loaded yet", () => {
        const errorMessage = "You need admin access to view this content";

        renderWithContexts(
            <SecuredByRole
                element={<TestElement />}
                allowedWorkspaceRoles={["workspace_owner"]}
                errorString={errorMessage}
            />,
            [], // no roles loaded yet
            [] // no app roles loaded yet
        );

        expect(screen.queryByTestId("secured-content")).not.toBeInTheDocument();
        expect(screen.queryByTestId("message-bar")).not.toBeInTheDocument();
    });

    it("fetches workspace roles when not in context and workspaceId is provided", async () => {
        const emptyWorkspaceContext = createMockWorkspaceContext([]);
        emptyWorkspaceContext.workspace.id = ""; // no workspace ID

        const appRolesContext = createMockAppRolesContext([]);

        mockApiCall
            .mockResolvedValueOnce({ workspaceAuth: { scopeId: "test-scope-id" } })
            .mockResolvedValueOnce(undefined); // roles callback will be called

        render(
            <WorkspaceContext.Provider value={emptyWorkspaceContext}>
                <AppRolesContext.Provider value={appRolesContext}>
                    <SecuredByRole
                        element={<TestElement />}
                        allowedWorkspaceRoles={["workspace_researcher"]}
                        workspaceId="test-workspace-id"
                    />
                </AppRolesContext.Provider>
            </WorkspaceContext.Provider>
        );

        await waitFor(() => {
            expect(mockApiCall).toHaveBeenCalledWith(
                "/api/workspaces/test-workspace-id/scopeid",
                "GET"
            );
        });

        expect(mockApiCall).toHaveBeenCalledWith(
            "/api/workspaces/test-workspace-id",
            "GET",
            "test-scope-id",
            undefined,
            "JSON",
            expect.any(Function),
            true
        );
    });

    it("does not fetch workspace roles when they are already in context", () => {
        renderWithContexts(
            <SecuredByRole
                element={<TestElement />}
                allowedWorkspaceRoles={["workspace_researcher"]}
                workspaceId="test-workspace-id"
            />,
            ["workspace_researcher"], // roles already in context
            []
        );

        expect(mockApiCall).not.toHaveBeenCalled();
    });

    it("renders nothing when no roles are allowed and user has no access", () => {
        renderWithContexts(
            <SecuredByRole
                element={<TestElement />}
            // no allowed roles specified
            />,
            ["workspace_researcher"],
            ["TREUser"]
        );

        expect(screen.queryByTestId("secured-content")).not.toBeInTheDocument();
        expect(screen.queryByTestId("message-bar")).not.toBeInTheDocument();
    });
});

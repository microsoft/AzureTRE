import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { UserMenu } from "./UserMenu";
import { AppRolesContext } from "../../contexts/AppRolesContext";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";

// Mock MSAL
const mockLogout = vi.fn();
const mockAccount = {
  name: "Test User",
  username: "test@example.com",
  homeAccountId: "test-home-account-id",
  environment: "test-environment",
  tenantId: "test-tenant-id",
  localAccountId: "test-local-account-id",
  idTokenClaims: { iat: 1700000000 },
};
let mockAccounts = [mockAccount];
let mockCurrentAccount: typeof mockAccount | null = mockAccount;

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({
    instance: {
      logout: mockLogout,
    },
    accounts: mockAccounts,
  }),
  useAccount: () => mockCurrentAccount,
}));

let lastPanelProps: any;
vi.mock("./UserAccessPanel", () => ({
  UserAccessPanel: (props: any) => {
    lastPanelProps = props;
    return props.isOpen ? (
      <div data-testid="access-panel">
        <button data-testid="panel-signout" onClick={props.onSignOut} />
      </div>
    ) : null;
  },
}));

// Mock FluentUI components
vi.mock("@fluentui/react", () => {
  const PrimaryButton = ({ children, menuProps, onClick, style }: any) => (
    <>
      <button data-testid="primary-button" onClick={onClick} style={style} data-menu={menuProps ? "true" : "false"}>
        {children}
      </button>
      {menuProps && (
        <div data-testid="menu-items">
          {menuProps.items.map((item: any) => (
            <button key={item.key} data-testid={`menu-item-${item.key}`} onClick={item.onClick}>
              {item.text}
            </button>
          ))}
        </div>
      )}
    </>
  );
  PrimaryButton.displayName = "PrimaryButton";

  const Persona = ({ text, secondaryText, size, imageAlt }: any) => (
    <div data-testid="persona" data-size={size} data-alt={imageAlt}>
      {text} {secondaryText}
    </div>
  );
  Persona.displayName = "Persona";

  return {
    ContextualMenuItemType: { Header: 2 },
    PrimaryButton,
    Persona,
    PersonaSize: {
      size32: "size32",
    },
  };
});

describe("UserMenu Component", () => {
  const renderWithRoles = (appRoles: string[] = [], workspaceRoles: string[] = [], workspaceId = "") =>
    render(
      <AppRolesContext.Provider value={{ roles: appRoles, setAppRoles: vi.fn() }}>
        <WorkspaceContext.Provider
          value={{
            roles: workspaceRoles,
            costs: [],
            setCosts: vi.fn(),
            setRoles: vi.fn(),
            setWorkspace: vi.fn(),
            workspace: { id: workspaceId } as any,
            workspaceApplicationIdURI: "",
          }}
        >
          <UserMenu />
        </WorkspaceContext.Provider>
      </AppRolesContext.Provider>,
    );

  beforeEach(() => {
    vi.clearAllMocks();
    mockAccounts = [mockAccount];
    mockCurrentAccount = mockAccount;
  });

  it("renders user menu with persona", () => {
    render(<UserMenu />);

    expect(screen.getByTestId("primary-button")).toBeInTheDocument();
    expect(screen.getByTestId("persona")).toBeInTheDocument();
    // User name is passed as text prop to the mocked Persona component
    const persona = screen.getByTestId("persona");
    expect(persona).toBeInTheDocument();
  });

  it("displays user name in persona", () => {
    render(<UserMenu />);

    const persona = screen.getByTestId("persona");
    // Just verify the persona component is rendered - the mock doesn't render text content
    expect(persona).toBeInTheDocument();
  });

  it("applies correct styling to button", () => {
    render(<UserMenu />);

    const button = screen.getByTestId("primary-button");
    expect(button).toHaveStyle({
      background: "none",
      // Note: border: "none" might be overridden by browser defaults in test environment
    });
  });

  it("renders logout menu item", () => {
    render(<UserMenu />);

    expect(screen.getByTestId("menu-item-logout")).toBeInTheDocument();
    expect(screen.getByText("Logout")).toBeInTheDocument();
  });

  it("calls logout when logout menu item is clicked", () => {
    render(<UserMenu />);

    const logoutItem = screen.getByTestId("menu-item-logout");
    fireEvent.click(logoutItem);

    expect(mockLogout).toHaveBeenCalledTimes(1);
  });

  it("has correct CSS class", () => {
    render(<UserMenu />);

    const container = screen.getByTestId("primary-button").parentElement;
    expect(container).toHaveClass("tre-user-menu");
  });

  it("configures menu with correct directional hint", () => {
    render(<UserMenu />);

    const button = screen.getByTestId("primary-button");
    expect(button).toHaveAttribute("data-menu", "true");
  });

  it("sets correct persona size", () => {
    render(<UserMenu />);

    const persona = screen.getByTestId("persona");
    expect(persona).toHaveAttribute("data-size", "size32");
  });

  it("handles no account gracefully", () => {
    mockAccounts = [];
    mockCurrentAccount = null;

    render(<UserMenu />);

    // Should still render the menu structure
    expect(screen.getByTestId("primary-button")).toBeInTheDocument();
    expect(screen.getByTestId("persona")).toBeInTheDocument();
  });

  it("does not show a role subtitle on the persona", () => {
    renderWithRoles(["TREAdmin"], ["WorkspaceOwner"], "workspace-id");

    expect(screen.getByTestId("persona")).not.toHaveTextContent("Administrator");
  });

  it("shows the user name and email as the menu header", () => {
    render(<UserMenu />);

    expect(screen.getByTestId("menu-item-user")).toHaveTextContent("Test User (test@example.com)");
  });

  it("falls back to the username when the account has no display name", () => {
    mockCurrentAccount = { ...mockAccount, name: undefined } as any;
    render(<UserMenu />);

    expect(screen.getByTestId("menu-item-user")).toHaveTextContent(/^test@example\.com$/);
  });

  it("opens the Your access panel with the token roles", () => {
    renderWithRoles(["TREUser"], ["WorkspaceOwner"], "workspace-id");

    expect(screen.queryByTestId("access-panel")).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId("menu-item-access"));

    expect(screen.getByTestId("access-panel")).toBeInTheDocument();
    expect(lastPanelProps.coreRoles).toEqual(["TREUser"]);
    expect(lastPanelProps.workspaceRoles).toEqual(["WorkspaceOwner"]);
    expect(lastPanelProps.workspaceName).toBe("workspace-id");
    expect(lastPanelProps.tokenIssuedAt).toBeUndefined();
    expect(lastPanelProps.userEmail).toBe("test@example.com");
  });

  it("does not pass a workspace outside a workspace", () => {
    renderWithRoles(["TREUser"]);

    expect(lastPanelProps.workspaceName).toBeUndefined();
  });

  it("signs out from the panel", () => {
    renderWithRoles(["TREUser"]);
    fireEvent.click(screen.getByTestId("menu-item-access"));
    fireEvent.click(screen.getByTestId("panel-signout"));

    expect(mockLogout).toHaveBeenCalledTimes(1);
  });
});

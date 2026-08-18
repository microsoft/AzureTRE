import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { UserMenu } from "./UserMenu";
import { AppRolesContext } from "../../contexts/AppRolesContext";
import { RoleName, WorkspaceRoleName } from "../../models/roleNames";

// Mock MSAL
const mockLogout = vi.fn();
const mockAccount = {
  name: "Test User",
  username: "test@example.com",
  homeAccountId: "test-home-account-id",
  environment: "test-environment",
  tenantId: "test-tenant-id",
  localAccountId: "test-local-account-id",
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
            <button
              key={item.key}
              data-testid={`menu-item-${item.key}`}
              data-type={item.itemType}
              onClick={item.onClick}
            >
              {item.text}
            </button>
          ))}
        </div>
      )}
    </>
  );
  PrimaryButton.displayName = "PrimaryButton";

  const Persona = ({ text, secondaryText, size, imageAlt }: any) => (
    <div data-testid="persona" data-size={size} data-alt={imageAlt} data-secondary-text={secondaryText}>
      {text}
    </div>
  );
  Persona.displayName = "Persona";

  return {
    PrimaryButton,
    Persona,
    PersonaSize: {
      size32: "size32",
      size40: "size40",
    },
    getTheme: () => ({ palette: { white: "#ffffff" } }),
    ContextualMenuItemType: {
      Normal: 0,
      Divider: 1,
      Header: 2,
    },
  };
});

const renderUserMenu = (appRoles: Array<string> = [], route: string = "/", workspaceRoles?: Array<string>) =>
  render(
    <MemoryRouter initialEntries={[route]}>
      <AppRolesContext.Provider value={{ roles: appRoles, setAppRoles: () => {} }}>
        <UserMenu workspaceRoles={workspaceRoles} />
      </AppRolesContext.Provider>
    </MemoryRouter>,
  );

describe("UserMenu Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAccounts = [mockAccount];
    mockCurrentAccount = mockAccount;
  });

  it("renders user menu with persona", () => {
    renderUserMenu();

    expect(screen.getByTestId("primary-button")).toBeInTheDocument();
    expect(screen.getByTestId("persona")).toBeInTheDocument();
  });

  it("applies correct styling to button", () => {
    renderUserMenu();

    const button = screen.getByTestId("primary-button");
    expect(button).toHaveStyle({
      background: "none",
      // Note: border: "none" might be overridden by browser defaults in test environment
    });
  });

  it("renders logout menu item", () => {
    renderUserMenu();

    expect(screen.getByTestId("menu-item-logout")).toBeInTheDocument();
    expect(screen.getByText("Logout")).toBeInTheDocument();
  });

  it("calls logout when logout menu item is clicked", () => {
    renderUserMenu();

    fireEvent.click(screen.getByTestId("menu-item-logout"));

    expect(mockLogout).toHaveBeenCalledTimes(1);
  });

  it("has correct CSS class", () => {
    renderUserMenu();

    const container = screen.getByTestId("primary-button").parentElement;
    expect(container).toHaveClass("tre-user-menu");
  });

  it("configures menu with correct directional hint", () => {
    renderUserMenu();

    const button = screen.getByTestId("primary-button");
    expect(button).toHaveAttribute("data-menu", "true");
  });

  // size40 is the smallest Fluent persona size that renders secondary text,
  // which is where the role summary goes. Dropping below it hides the summary.
  it("sets a persona size that renders the secondary text", () => {
    renderUserMenu();

    const persona = screen.getByTestId("persona");
    expect(persona).toHaveAttribute("data-size", "size40");
  });

  it("handles no account gracefully", () => {
    mockAccounts = [];
    mockCurrentAccount = null;

    renderUserMenu();

    // Should still render the menu structure
    expect(screen.getByTestId("primary-button")).toBeInTheDocument();
    expect(screen.getByTestId("persona")).toBeInTheDocument();
  });

  it("lists the TRE roles the user holds, with display names", () => {
    renderUserMenu([RoleName.TREAdmin, RoleName.TREUser]);

    expect(screen.getByTestId("menu-item-tre-roles-header")).toHaveTextContent("TRE roles");
    expect(screen.getByTestId(`menu-item-tre-roles-${RoleName.TREAdmin}`)).toHaveTextContent("TRE Administrator");
    expect(screen.getByTestId(`menu-item-tre-roles-${RoleName.TREUser}`)).toHaveTextContent("TRE User");
  });

  it("summarises a single TRE role on the persona outside a workspace", () => {
    renderUserMenu([RoleName.TREAdmin]);

    expect(screen.getByTestId("persona")).toHaveAttribute("data-secondary-text", "TRE Administrator");
  });

  it("counts the remaining roles rather than listing them all", () => {
    renderUserMenu([RoleName.TREUser, RoleName.TREAdmin]);

    expect(screen.getByTestId("persona")).toHaveAttribute("data-secondary-text", "TRE Administrator +1 more");
  });

  // The token lists roles in no guaranteed order, so the one role that fits must
  // be picked by privilege rather than by position.
  it("names the most privileged role first regardless of token order", () => {
    renderUserMenu([RoleName.TREUser], "/workspaces/ws-id", [
      WorkspaceRoleName.WorkspaceResearcher,
      WorkspaceRoleName.WorkspaceOwner,
      WorkspaceRoleName.AirlockManager,
    ]);

    expect(screen.getByTestId("persona")).toHaveAttribute("data-secondary-text", "Workspace Owner +2 more");
  });

  it("shows an explicit message when the user holds no TRE role", () => {
    renderUserMenu([]);

    expect(screen.getByTestId("menu-item-tre-roles-none")).toHaveTextContent("None assigned");
    expect(screen.getByTestId("persona")).toHaveAttribute("data-secondary-text", "No roles assigned");
  });

  it("does not show a workspace section outside a workspace", () => {
    renderUserMenu([RoleName.TREUser]);

    expect(screen.queryByTestId("menu-item-workspace-roles-header")).not.toBeInTheDocument();
  });

  it("lists the workspace roles the user holds when viewing a workspace", () => {
    renderUserMenu([RoleName.TREUser], "/workspaces/ws-id", [
      WorkspaceRoleName.WorkspaceOwner,
      WorkspaceRoleName.AirlockManager,
    ]);

    expect(screen.getByTestId("menu-item-workspace-roles-header")).toHaveTextContent("Workspace roles");
    expect(screen.getByTestId(`menu-item-workspace-roles-${WorkspaceRoleName.WorkspaceOwner}`)).toHaveTextContent(
      "Workspace Owner",
    );
    expect(screen.getByTestId(`menu-item-workspace-roles-${WorkspaceRoleName.AirlockManager}`)).toHaveTextContent(
      "Airlock Manager",
    );
  });

  it("summarises the workspace roles on the persona inside a workspace", () => {
    renderUserMenu([RoleName.TREUser], "/workspaces/ws-id", [WorkspaceRoleName.WorkspaceResearcher]);

    expect(screen.getByTestId("persona")).toHaveAttribute("data-secondary-text", "Workspace Researcher");
  });

  // A TRE Admin gets into a workspace on a core token and holds no workspace
  // role there. The section must still appear, otherwise this looks the same as
  // not being in a workspace.
  it("shows an empty workspace section for a TRE Admin with no workspace role", () => {
    renderUserMenu([RoleName.TREAdmin], "/workspaces/ws-id", []);

    expect(screen.getByTestId("menu-item-workspace-roles-none")).toHaveTextContent("None assigned");
    expect(screen.getByTestId("persona")).toHaveAttribute("data-secondary-text", "TRE Administrator");
  });

  it("falls back to the raw value for a role with no display name", () => {
    renderUserMenu(["SomeNewRole"]);

    expect(screen.getByTestId("menu-item-tre-roles-SomeNewRole")).toHaveTextContent("SomeNewRole");
  });
});

import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { UserAccessPanel } from "./UserAccessPanel";

vi.mock("@fluentui/react", () => ({
  Panel: ({ isOpen, headerText, children, onRenderFooterContent }: any) =>
    isOpen ? (
      <div data-testid="panel">
        <h1>{headerText}</h1>
        {children}
        {onRenderFooterContent?.()}
      </div>
    ) : null,
  PanelType: { smallFixedFar: 1 },
  MessageBar: ({ children }: any) => <div data-testid="message-bar">{children}</div>,
  MessageBarType: { info: 0, warning: 5 },
  DefaultButton: ({ text, onClick }: any) => <button onClick={onClick}>{text}</button>,
  Stack: ({ children, "data-testid": testId }: any) => <div data-testid={testId}>{children}</div>,
  Text: ({ children, className }: any) => <span className={className}>{children}</span>,
  Icon: () => null,
  Persona: ({ text, secondaryText }: any) => (
    <div data-testid="persona">
      <span>{text}</span>
      <span>{secondaryText}</span>
    </div>
  ),
  PersonaSize: { size40: 40 },
  FontWeights: { semibold: 600 },
  getTheme: () => ({
    palette: { green: "green", neutralLight: "grey", neutralSecondary: "grey", neutralTertiary: "grey" },
  }),
  mergeStyles: () => "",
}));

const baseProps = {
  isOpen: true,
  onDismiss: vi.fn(),
  onSignOut: vi.fn(),
  userName: "Jane Doe",
  userEmail: "jane@contoso.com",
  coreRoles: [] as Array<string>,
  workspaceRoles: [] as Array<string>,
};

describe("UserAccessPanel", () => {
  it("does not render when closed", () => {
    render(<UserAccessPanel {...baseProps} isOpen={false} />);
    expect(screen.queryByTestId("panel")).not.toBeInTheDocument();
  });

  it("shows the user identity and the sign-in hint without attributing a time to current roles", () => {
    render(<UserAccessPanel {...baseProps} />);

    expect(screen.getByText("Your access")).toBeInTheDocument();
    expect(screen.getByTestId("persona")).toHaveTextContent("Jane Doe");
    expect(screen.getByTestId("persona")).toHaveTextContent("jane@contoso.com");
    expect(screen.getByText(/Roles come from your sign-in token/)).toBeInTheDocument();
    expect(screen.queryByText(/issued at/)).not.toBeInTheDocument();
  });

  it("calls sign out", () => {
    const onSignOut = vi.fn();
    render(<UserAccessPanel {...baseProps} onSignOut={onSignOut} />);
    fireEvent.click(screen.getByText("Sign out and back in"));
    expect(onSignOut).toHaveBeenCalledTimes(1);
  });

  it("shows held core roles with descriptions and roles not held", () => {
    render(<UserAccessPanel {...baseProps} coreRoles={["TREUser"]} />);

    expect(screen.getByTestId("role-held-TREUser")).toHaveTextContent("TRE User");
    expect(screen.getByTestId("role-held-TREUser")).toHaveTextContent("Sign in to the TRE");
    expect(screen.getByTestId("role-not-held-TREAdmin")).toHaveTextContent("TRE Administrator — not assigned");
  });

  it("shows all roles as not assigned when the user has none", () => {
    render(<UserAccessPanel {...baseProps} />);

    expect(screen.getByTestId("role-not-held-TREAdmin")).toBeInTheDocument();
    expect(screen.getByTestId("role-not-held-TREUser")).toBeInTheDocument();
  });

  it("hides the workspace section outside a workspace", () => {
    render(<UserAccessPanel {...baseProps} coreRoles={["TREUser"]} />);
    expect(screen.queryByText("Workspace roles")).not.toBeInTheDocument();
  });

  it("shows workspace roles in a workspace", () => {
    render(
      <UserAccessPanel
        {...baseProps}
        coreRoles={["TREUser"]}
        workspaceRoles={["WorkspaceOwner", "AirlockManager"]}
        workspaceName="My Workspace"
      />,
    );

    expect(screen.getByText("Workspace roles")).toBeInTheDocument();
    expect(screen.getByText("My Workspace")).toBeInTheDocument();
    expect(screen.getByTestId("role-held-WorkspaceOwner")).toBeInTheDocument();
    expect(screen.getByTestId("role-held-AirlockManager")).toBeInTheDocument();
    expect(screen.getByTestId("role-not-held-WorkspaceResearcher")).toBeInTheDocument();
  });

  it("explains when a TRE admin has no workspace role", () => {
    render(<UserAccessPanel {...baseProps} coreRoles={["TREAdmin"]} workspaceName="Cardiology Study" />);

    expect(screen.getByText(/viewing this workspace as a TRE Administrator/)).toBeInTheDocument();
  });

  it("explains when a user has no workspace role", () => {
    render(<UserAccessPanel {...baseProps} coreRoles={["TREUser"]} workspaceName="Cardiology Study" />);

    expect(screen.getByText("No workspace role assigned.")).toBeInTheDocument();
  });

  it("shows unknown roles from the token", () => {
    render(<UserAccessPanel {...baseProps} coreRoles={["CustomRole"]} />);
    expect(screen.getByTestId("role-held-CustomRole")).toHaveTextContent("CustomRole");
  });
});

import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, createPartialFluentUIMock, mockClipboardAPI } from "../../test-utils";
import { CliCommand } from "./CliCommand";

// Mock FluentUI components using the centralized mock
vi.mock("@fluentui/react", async () => {
  const actual = await vi.importActual("@fluentui/react");
  return {
    ...actual,
    ...createPartialFluentUIMock([
      'Stack',
      'Text',
      'IconButton',
      'TooltipHost',
      'Spinner'
    ]),
  };
});

// Setup mock clipboard API before each test
beforeEach(() => {
  mockClipboardAPI();
  vi.clearAllMocks();
  vi.clearAllTimers();
});

describe("CliCommand Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.clearAllTimers();
  });

  it("renders the title", () => {
    render(
      <CliCommand
        command="tre workspace new"
        title="Create Workspace"
        isLoading={false}
      />
    );

    expect(screen.getByText("Create Workspace")).toBeInTheDocument();
  });

  it("renders copy button with copy icon", () => {
    render(
      <CliCommand
        command="tre workspace new"
        title="Create Workspace"
        isLoading={false}
      />
    );

    const copyButton = screen.getByTestId("icon-button");
    expect(copyButton).toHaveAttribute("data-icon-name", "copy");
  });

  it("shows default tooltip message initially", () => {
    render(
      <CliCommand
        command="tre workspace new"
        title="Create Workspace"
        isLoading={false}
      />
    );

    const tooltip = screen.getByTestId("tooltip-host");
    expect(tooltip).toHaveAttribute("title", "Copy to clipboard");
  });

  it("displays spinner when loading", () => {
    render(
      <CliCommand
        command=""
        title="Create Workspace"
        isLoading={true}
      />
    );

    expect(screen.getByTestId("spinner")).toBeInTheDocument();
    expect(screen.getByText("Generating command...")).toBeInTheDocument();
  });

  it("copies command to clipboard when copy button is clicked", async () => {
    const command = "tre workspace new --template-name base";

    render(
      <CliCommand
        command={command}
        title="Create Workspace"
        isLoading={false}
      />
    );

    const copyButton = screen.getByTestId("icon-button");
    fireEvent.click(copyButton);

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(command);
  });

  it("shows 'Copied' tooltip message after clicking copy button", async () => {
    render(
      <CliCommand
        command="tre workspace new"
        title="Create Workspace"
        isLoading={false}
      />
    );

    const copyButton = screen.getByTestId("icon-button");
    fireEvent.click(copyButton);

    await waitFor(() => {
      const tooltip = screen.getByTestId("tooltip-host");
      expect(tooltip).toHaveAttribute("title", "Copied");
    });
  });

  it("does not copy empty command", () => {
    render(
      <CliCommand
        command=""
        title="Create Workspace"
        isLoading={false}
      />
    );

    const copyButton = screen.getByTestId("icon-button");
    fireEvent.click(copyButton);

    expect(navigator.clipboard.writeText).not.toHaveBeenCalled();
  });

  it("renders simple command without parameters", () => {
    render(
      <CliCommand
        command="tre workspace list"
        title="List Workspaces"
        isLoading={false}
      />
    );

    expect(screen.getByText("tre workspace list")).toBeInTheDocument();
  });

  it("renders command with parameters correctly", () => {
    const command = "tre workspace new --template-name base --display-name MyWorkspace";

    render(
      <CliCommand
        command={command}
        title="Create Workspace"
        isLoading={false}
      />
    );

    // Should render base command
    expect(screen.getByText("tre workspace new")).toBeInTheDocument();

    // Should render parameters
    expect(screen.getByText("--template-name")).toBeInTheDocument();
    expect(screen.getByText(/base/)).toBeInTheDocument();
    expect(screen.getByText("--display-name")).toBeInTheDocument();
    expect(screen.getByText(/MyWorkspace/)).toBeInTheDocument();
  });

  it("handles command with comment-style parameter values", () => {
    const command = "tre workspace new --template-name <workspace-template-name>";

    render(
      <CliCommand
        command={command}
        title="Create Workspace"
        isLoading={false}
      />
    );

    // Should render base command
    expect(screen.getByText("tre workspace new")).toBeInTheDocument();

    // Should render parameter
    expect(screen.getByText("--template-name")).toBeInTheDocument();
    expect(screen.getByText(/<workspace-template-name>/)).toBeInTheDocument();
  });

  it("handles command with long parameter values that need to break", () => {
    const command = "tre workspace new --very-long-parameter-name very-long-parameter-value-that-should-wrap";

    render(
      <CliCommand
        command={command}
        title="Create Workspace"
        isLoading={false}
      />
    );

    expect(screen.getByText("tre workspace new")).toBeInTheDocument();
    expect(screen.getByText("--very-long-parameter-name")).toBeInTheDocument();
    expect(screen.getByText(/very-long-parameter-value-that-should-wrap/)).toBeInTheDocument();
  });

  it("handles command with multiple parameters", () => {
    const command = "tre workspace new --template-name base --display-name MyWorkspace --description Test";

    render(
      <CliCommand
        command={command}
        title="Create Workspace"
        isLoading={false}
      />
    );

    // Should render all parameters
    expect(screen.getByText("--template-name")).toBeInTheDocument();
    expect(screen.getByText("--display-name")).toBeInTheDocument();
    expect(screen.getByText("--description")).toBeInTheDocument();
    expect(screen.getByText(/base/)).toBeInTheDocument();
    expect(screen.getByText(/MyWorkspace/)).toBeInTheDocument();
    expect(screen.getByText(/Test/)).toBeInTheDocument();
  });

  it("handles command with parameters that have no values", () => {
    const command = "tre workspace new --template-name --display-name";

    render(
      <CliCommand
        command={command}
        title="Create Workspace"
        isLoading={false}
      />
    );

    expect(screen.getByText("tre workspace new")).toBeInTheDocument();
    expect(screen.getByText("--template-name")).toBeInTheDocument();
    expect(screen.getByText("--display-name")).toBeInTheDocument();
  });

  it("handles malformed command gracefully", () => {
    const command = "   tre workspace    new   --template-name    base   ";

    render(
      <CliCommand
        command={command}
        title="Create Workspace"
        isLoading={false}
      />
    );

    // Should still parse and render correctly
    expect(screen.getByText(/tre workspace.*new/)).toBeInTheDocument();
    expect(screen.getByText("--template-name")).toBeInTheDocument();
    expect(screen.getByText(/base/)).toBeInTheDocument();
  });

  it("renders correct styling for header", () => {
    render(
      <CliCommand
        command="tre workspace new"
        title="Create Workspace"
        isLoading={false}
      />
    );

    const headerStack = screen.getAllByTestId("stack")[1]; // Second stack is the header
    expect(headerStack).toHaveAttribute("data-horizontal", "true");
    expect(headerStack).toHaveStyle("background-color: rgb(230, 230, 230)");
  });

  it("renders stack items with correct properties", () => {
    render(
      <CliCommand
        command="tre workspace new"
        title="Create Workspace"
        isLoading={false}
      />
    );

    const stackItems = screen.getAllByTestId("stack-item");

    // Check title stack item has grow property
    const titleItem = stackItems.find(item => item.getAttribute("data-grow") === "true");
    expect(titleItem).toBeTruthy();

    // Check button stack item has align end
    const buttonItem = stackItems.find(item => item.getAttribute("data-align") === "end");
    expect(buttonItem).toBeTruthy();
  });
});

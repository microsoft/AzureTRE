import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { VMPowerButton } from "./VMPowerButton";
import { ComponentAction, Resource, VMPowerStates } from "../../models/resource";
import { ResourceType } from "../../models/resourceType";

const mockInvokeAction = vi.fn().mockResolvedValue(undefined);
let mockCustomActions: Array<{ name: string; description: string }> = [];

vi.mock("../../hooks/useResourceTemplate", () => ({
  useResourceTemplate: () => ({
    resourceTemplate: { customActions: mockCustomActions },
    parentResource: {},
    roles: ["WorkspaceResearcher"],
  }),
}));

vi.mock("../../hooks/useInvokeResourceAction", () => ({
  useInvokeResourceAction: () => mockInvokeAction,
}));

vi.mock("./SecuredByRole", () => ({
  SecuredByRole: ({ element }: any) => element,
}));

vi.mock("./ConfirmStopVM", () => ({
  ConfirmStopVM: ({ onConfirm, onDismiss }: any) => (
    <div role="dialog">
      <button onClick={onConfirm}>Stop VM</button>
      <button onClick={onDismiss}>Cancel</button>
    </div>
  ),
}));

vi.mock("./ExceptionLayout", () => ({
  ExceptionLayout: ({ e, onRetry }: any) => (
    <div>
      <span>{e.userMessage}</span>
      <button onClick={onRetry}>Retry action</button>
    </div>
  ),
}));

vi.mock("@fluentui/react", () => ({
  DefaultButton: ({ text, onClick, disabled, title }: any) => (
    <button onClick={onClick} disabled={disabled} title={title}>
      {text}
    </button>
  ),
  IconButton: ({ ariaLabel, onClick, disabled, title }: any) => (
    <button aria-label={ariaLabel} onClick={onClick} disabled={disabled} title={title} />
  ),
}));

const vm = (powerState: VMPowerStates, overrides: Partial<Resource> = {}) =>
  ({
    id: "vm-1",
    resourceType: ResourceType.UserResource,
    resourcePath: "/workspaces/ws/workspace-services/svc/user-resources/vm-1",
    templateName: "tre-service-guacamole-linuxvm",
    isEnabled: true,
    deploymentStatus: "deployed",
    properties: { display_name: "VM" },
    azureStatus: { powerState },
    ...overrides,
  }) as unknown as Resource;

describe("VMPowerButton", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCustomActions = [
      { name: "start", description: "Start the VM" },
      { name: "stop", description: "Stop the VM" },
    ];
  });

  it("starts a stopped VM straight away", () => {
    render(<VMPowerButton resource={vm(VMPowerStates.Deallocated)} componentAction={ComponentAction.None} />);

    fireEvent.click(screen.getByRole("button", { name: "Start" }));

    expect(mockInvokeAction).toHaveBeenCalledWith(expect.objectContaining({ id: "vm-1" }), "start");
  });

  it("shows a retryable error when a VM action fails and retries that action", async () => {
    mockInvokeAction.mockRejectedValueOnce({ status: 503, userMessage: "API unavailable" });
    mockInvokeAction.mockResolvedValueOnce(undefined);
    render(<VMPowerButton resource={vm(VMPowerStates.Deallocated)} componentAction={ComponentAction.None} />);

    fireEvent.click(screen.getByRole("button", { name: "Start" }));
    expect(await screen.findByText("API unavailable")).toBeInTheDocument();
    expect(mockInvokeAction).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "Retry action" }));
    await waitFor(() => expect(mockInvokeAction).toHaveBeenCalledTimes(2));
    expect(mockInvokeAction).toHaveBeenNthCalledWith(2, expect.objectContaining({ id: "vm-1" }), "start");
  });

  it("closes a Stop confirmation when polling shows the VM has stopped", () => {
    const { rerender } = render(
      <VMPowerButton resource={vm(VMPowerStates.Running)} componentAction={ComponentAction.None} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Stop" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    rerender(<VMPowerButton resource={vm(VMPowerStates.Deallocated)} componentAction={ComponentAction.None} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("resets pending state and errors when the resource changes", async () => {
    mockInvokeAction.mockRejectedValueOnce({ status: 503, userMessage: "API unavailable" });
    const { rerender } = render(
      <VMPowerButton resource={vm(VMPowerStates.Deallocated)} componentAction={ComponentAction.None} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Start" }));
    expect(await screen.findByText("API unavailable")).toBeInTheDocument();

    rerender(
      <VMPowerButton
        resource={vm(VMPowerStates.Deallocated, { id: "vm-2" } as Partial<Resource>)}
        componentAction={ComponentAction.None}
      />,
    );
    expect(screen.queryByText("API unavailable")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start" })).toBeEnabled();
  });

  it("keeps the button usable after switching resource while a request is pending", async () => {
    let resolve: () => void = () => undefined;
    mockInvokeAction.mockImplementationOnce(() => new Promise<void>((r) => (resolve = r)));
    const { rerender } = render(
      <VMPowerButton resource={vm(VMPowerStates.Deallocated)} componentAction={ComponentAction.None} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Start" }));
    expect(screen.getByRole("button", { name: "Start" })).toBeDisabled();

    rerender(
      <VMPowerButton
        resource={vm(VMPowerStates.Deallocated, { id: "vm-2" } as Partial<Resource>)}
        componentAction={ComponentAction.None}
      />,
    );
    expect(screen.getByRole("button", { name: "Start" })).toBeEnabled();
    resolve();
  });

  it("describes a failed stop correctly", async () => {
    mockInvokeAction.mockRejectedValueOnce({ status: 400 });
    render(<VMPowerButton resource={vm(VMPowerStates.Running)} componentAction={ComponentAction.None} />);

    fireEvent.click(screen.getByRole("button", { name: "Stop" }));
    fireEvent.click(screen.getByRole("button", { name: "Stop VM" }));

    expect(await screen.findByText("Error stopping virtual machine")).toBeInTheDocument();
  });

  it("asks for confirmation before stopping a running VM", () => {
    render(<VMPowerButton resource={vm(VMPowerStates.Running)} componentAction={ComponentAction.None} />);

    fireEvent.click(screen.getByRole("button", { name: "Stop" }));
    expect(mockInvokeAction).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Stop VM" }));
    expect(mockInvokeAction).toHaveBeenCalledWith(expect.objectContaining({ id: "vm-1" }), "stop");
  });

  it("is disabled while the VM is changing state or the resource is locked", () => {
    const { rerender } = render(
      <VMPowerButton resource={vm(VMPowerStates.Starting)} componentAction={ComponentAction.None} />,
    );
    expect(screen.getByRole("button", { name: "Starting" })).toBeDisabled();

    rerender(<VMPowerButton resource={vm(VMPowerStates.Running)} componentAction={ComponentAction.Lock} />);
    expect(screen.getByRole("button", { name: "Stop" })).toBeDisabled();
  });

  it("is not shown for resources that aren't VMs or whose template has no start and stop actions", () => {
    const { container, rerender } = render(
      <VMPowerButton
        resource={vm(VMPowerStates.Running, { azureStatus: {} } as Partial<Resource>)}
        componentAction={ComponentAction.None}
      />,
    );
    expect(container).toBeEmptyDOMElement();

    mockCustomActions = [{ name: "reset_password", description: "" }];
    rerender(<VMPowerButton resource={vm(VMPowerStates.Running)} componentAction={ComponentAction.None} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders an icon-only button with an accessible name for cards", () => {
    render(<VMPowerButton resource={vm(VMPowerStates.Deallocated)} componentAction={ComponentAction.None} iconOnly />);

    const button = screen.getByRole("button", { name: "Start" });
    expect(button).toBeEmptyDOMElement();
    expect(button).toHaveAttribute("title", "Start: power on the VM");
  });
});

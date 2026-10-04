import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ResourceContextMenu } from "./ResourceContextMenu";
import { ComponentAction, Resource, VMPowerStates } from "../../models/resource";
import { ResourceType } from "../../models/resourceType";

const mockInvokeAction = vi.fn().mockResolvedValue(undefined);
const templateActions = vi.hoisted(() => ({ current: [{ name: "stop", description: "Stop the pipeline" }] as any[] }));

vi.mock("../../hooks/useResourceTemplate", () => ({
  useResourceTemplate: () => ({
    resourceTemplate: { customActions: templateActions.current },
    parentResource: {},
    roles: ["WorkspaceOwner"],
  }),
}));

vi.mock("../../hooks/useInvokeResourceAction", () => ({
  useInvokeResourceAction: () => mockInvokeAction,
}));

vi.mock("./SecuredByRole", () => ({
  SecuredByRole: ({ element }: any) => element,
}));

vi.mock("./ConfirmStopVM", () => ({
  ConfirmStopVM: () => <div role="dialog">Stop VM?</div>,
}));

vi.mock("./ExceptionLayout", () => ({
  ExceptionLayout: ({ e, onRetry }: any) => (
    <div role="alert">
      {e.userMessage}
      <button onClick={onRetry}>Retry</button>
    </div>
  ),
}));

// Render command bar items, including sub-menu items, as plain buttons.
vi.mock("@fluentui/react", async (importOriginal) => {
  const actual: any = await importOriginal();
  const renderItems = (items: any[]): any =>
    items.map((item) => (
      <div key={item.key}>
        <button title={item.title} onClick={item.onClick} disabled={item.disabled}>
          {item.text}
        </button>
        {item.subMenuProps && renderItems(item.subMenuProps.items)}
      </div>
    ));
  return { ...actual, CommandBar: ({ items }: any) => <div>{renderItems(items)}</div> };
});

const resource = (overrides: Partial<Resource>) =>
  ({
    id: "resource-1",
    resourceType: ResourceType.UserResource,
    resourcePath: "/workspaces/ws/workspace-services/svc/user-resources/resource-1",
    templateName: "template",
    isEnabled: true,
    deploymentStatus: "deployed",
    properties: { display_name: "Resource" },
    ...overrides,
  }) as unknown as Resource;

describe("ResourceContextMenu custom actions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    templateActions.current = [{ name: "stop", description: "Stop the pipeline" }];
  });

  it("leaves Start/Stop to the VM power button when the VM has both actions", () => {
    templateActions.current = [
      { name: "start", description: "Start" },
      { name: "stop", description: "Stop" },
      { name: "resize", description: "Resize the VM" },
    ];
    render(
      <ResourceContextMenu
        resource={resource({ azureStatus: { powerState: VMPowerStates.Running } })}
        componentAction={ComponentAction.None}
        commandBar
      />,
    );

    expect(screen.queryByRole("button", { name: "Start" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Stop" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Resize" })).toBeInTheDocument();
  });

  it("shows an error with retry when a custom action fails", async () => {
    templateActions.current = [{ name: "resize", description: "Resize the VM" }];
    mockInvokeAction.mockRejectedValueOnce({ status: 500 });
    render(
      <ResourceContextMenu
        resource={resource({ resourceType: ResourceType.WorkspaceService })}
        componentAction={ComponentAction.None}
        commandBar
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Resize" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Error running Resize");

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
    expect(mockInvokeAction).toHaveBeenCalledTimes(2);
  });

  it("clears a previous resource's action error when the resource changes", async () => {
    templateActions.current = [{ name: "resize", description: "Resize the VM" }];
    mockInvokeAction.mockRejectedValueOnce({ status: 500 });
    const props = { componentAction: ComponentAction.None, commandBar: true };
    const { rerender } = render(
      <ResourceContextMenu resource={resource({ resourceType: ResourceType.WorkspaceService })} {...props} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Resize" }));
    expect(await screen.findByRole("alert")).toBeInTheDocument();

    rerender(
      <ResourceContextMenu
        resource={resource({ id: "resource-2", resourceType: ResourceType.WorkspaceService })}
        {...props}
      />,
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("ignores a failure that arrives after switching resource", async () => {
    templateActions.current = [{ name: "resize", description: "Resize the VM" }];
    let reject: (e: unknown) => void = () => undefined;
    mockInvokeAction.mockImplementationOnce(() => new Promise((_, r) => (reject = r)));
    const props = { componentAction: ComponentAction.None, commandBar: true };
    const { rerender } = render(
      <ResourceContextMenu resource={resource({ resourceType: ResourceType.WorkspaceService })} {...props} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Resize" }));
    rerender(
      <ResourceContextMenu
        resource={resource({ id: "resource-2", resourceType: ResourceType.WorkspaceService })}
        {...props}
      />,
    );
    await act(async () => reject({ status: 500 }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("keeps clicks on the action error from reaching a clickable parent card", async () => {
    templateActions.current = [{ name: "resize", description: "Resize the VM" }];
    mockInvokeAction.mockRejectedValueOnce({ status: 500 }).mockRejectedValueOnce({ status: 500 });
    const onCardClick = vi.fn();
    render(
      <div onClick={onCardClick}>
        <ResourceContextMenu
          resource={resource({ resourceType: ResourceType.WorkspaceService })}
          componentAction={ComponentAction.None}
          commandBar
        />
      </div>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Resize" }));
    onCardClick.mockClear();
    fireEvent.click(await screen.findByRole("button", { name: "Retry" }));
    expect(onCardClick).not.toHaveBeenCalled();
  });

  it("asks for VM confirmation before stopping a virtual machine", () => {
    render(
      <ResourceContextMenu
        resource={resource({ azureStatus: { powerState: VMPowerStates.Running } })}
        componentAction={ComponentAction.None}
        commandBar
      />,
    );

    const stop = screen.getByRole("button", { name: "Stop" });
    expect(stop).toHaveAttribute("title", "Power off the VM. You can start it again later.");
    fireEvent.click(stop);

    expect(screen.getByRole("dialog")).toHaveTextContent("Stop VM?");
    expect(mockInvokeAction).not.toHaveBeenCalled();
  });

  it("runs a non-VM stop action directly with its own description", () => {
    render(
      <ResourceContextMenu
        resource={resource({ resourceType: ResourceType.WorkspaceService })}
        componentAction={ComponentAction.None}
        commandBar
      />,
    );

    const stop = screen.getByRole("button", { name: "Stop" });
    expect(stop).toHaveAttribute("title", "Stop the pipeline");
    fireEvent.click(stop);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(mockInvokeAction).toHaveBeenCalledWith(expect.objectContaining({ id: "resource-1" }), "stop");
  });
});

import React from "react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ResourcePropertyPanel } from "./ResourcePropertyPanel";
import { ResourceOperationsList } from "./ResourceOperationsList";
import { ResourceHistoryList } from "./ResourceHistoryList";
import { Resource } from "../../models/resource";
import { ResourceType } from "../../models/resourceType";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";

const mockApiCall = vi.fn();
vi.mock("../../hooks/useAuthApiCall", () => ({
  useAuthApiCall: () => mockApiCall,
  HttpMethod: { Get: "GET" },
}));

vi.mock("./ErrorPanel", () => ({
  ErrorPanel: ({ isOpen, errorMessage }: any) => (isOpen ? <div role="dialog">{errorMessage}</div> : null),
}));

beforeAll(() => {
  // DetailsList constructs a ResizeObserver, so the mock must be a class.
  (window as any).ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
});

const resource = {
  id: "svc-1",
  resourceType: ResourceType.WorkspaceService,
  resourcePath: "/workspaces/ws/workspace-services/svc-1",
  templateName: "tre-service-guacamole",
  templateVersion: "0.14.6",
  isEnabled: true,
  resourceVersion: 2,
  updatedWhen: 1790000000,
  user: { id: "sp-id", name: "", email: "", roleAssignments: [], roles: [] },
  properties: {
    display_name: "Guacamole",
    is_exposed_externally: false,
    admin_connection_uri: "https://guac.example.com/guacamole",
    empty_value: "",
  },
} as unknown as Resource;

describe("ResourcePropertyPanel", () => {
  it("groups resource fields and formats property values", () => {
    render(<ResourcePropertyPanel resource={resource} />);

    expect(screen.getByText("Resource")).toBeInTheDocument();
    expect(screen.getByText("Properties")).toBeInTheDocument();
    expect(screen.getByText("Workspace service")).toBeInTheDocument();
    expect(screen.getByText("tre-service-guacamole (0.14.6)")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copy resource id" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "https://guac.example.com/guacamole" })).toBeInTheDocument();
    expect(screen.getByText("No")).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
    // Falls back to the user ID when the operation was made by a service principal without a name.
    expect(screen.getByText(/by sp-id/)).toBeInTheDocument();
  });
});

describe("ResourceHistoryList", () => {
  it("lists versions newest first, including the current one, with what changed", async () => {
    mockApiCall.mockResolvedValue({
      resource_history: [
        {
          resourceId: "svc-1",
          resourceVersion: 0,
          isEnabled: true,
          templateVersion: "0.14.5",
          updatedWhen: 1,
          user: { name: "Ann" },
          properties: { display_name: "Guac" },
        },
        {
          resourceId: "svc-1",
          resourceVersion: 1,
          isEnabled: true,
          templateVersion: "0.14.6",
          updatedWhen: 2,
          user: { name: "Bob" },
          properties: { display_name: "Guacamole" },
        },
      ],
    });
    render(<ResourceHistoryList resource={resource} />);

    await waitFor(() => expect(screen.getByText("Bob")).toBeInTheDocument());
    const rows = screen.getAllByRole("row").slice(1);
    expect(rows).toHaveLength(3);
    expect(rows[0]).toHaveTextContent("2 (current)");
    expect(rows[0]).toHaveTextContent("Is exposed externally: No");
    expect(rows[1]).toHaveTextContent("Display name: Guac → Guacamole");
    expect(rows[1]).toHaveTextContent("Template version: 0.14.5 → 0.14.6");
    expect(rows[2]).toHaveTextContent("Created");
    expect(screen.queryByText("svc-1")).not.toBeInTheDocument();
  });
});

describe("history and operations API scope", () => {
  it("uses the core token for a TRE Admin whose workspace role doesn't grant access", async () => {
    mockApiCall.mockResolvedValue({ resource_history: [] });
    const ctx = { roles: ["WorkspaceResearcher"], workspaceApplicationIdURI: "ws-scope", workspace: { id: "ws" } };
    render(
      <WorkspaceContext.Provider value={ctx as any}>
        <ResourceHistoryList resource={resource} allowedRoles={["TREAdmin", "WorkspaceOwner"]} />
      </WorkspaceContext.Provider>,
    );

    await waitFor(() => expect(mockApiCall).toHaveBeenCalledWith(expect.stringMatching(/history$/), "GET", ""));
  });
});

describe("ResourceOperationsList", () => {
  const step = (status: string, message: string) => ({ stepTitle: `Step ${status}`, status, message });

  it("collapses steps of completed operations and expands failed ones", async () => {
    mockApiCall.mockResolvedValue({
      operations: [
        {
          id: "op-1",
          action: "install",
          status: "deployed",
          resourceVersion: 0,
          message: "Done",
          createdWhen: 1,
          updatedWhen: 1,
          user: { name: "Ann" },
          steps: [step("deployed", "ok")],
        },
        {
          id: "op-2",
          action: "upgrade",
          status: "updating_failed",
          resourceVersion: 1,
          message: "Terraform failed",
          createdWhen: 2,
          updatedWhen: 2,
          user: { name: "Bob" },
          steps: [step("updated", "ok"), step("updating_failed", "Rule error")],
        },
      ],
    });
    render(<ResourceOperationsList resource={resource} />);

    await waitFor(() => expect(screen.getByText("Upgrade")).toBeInTheDocument());
    // Newest (failed) first and expanded; the completed install is collapsed.
    expect(screen.getByRole("button", { name: "2 steps" })).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("button", { name: "1 step" })).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Step deployed")).not.toBeInTheDocument();

    expect(screen.getByRole("img", { name: "Status: updating failed" })).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "View error details" })[0]);
    expect(screen.getByRole("dialog")).toHaveTextContent("Terraform failed");

    fireEvent.click(screen.getByRole("button", { name: "1 step" }));
    expect(screen.getByText(/Step deployed/)).toBeInTheDocument();
  });
});

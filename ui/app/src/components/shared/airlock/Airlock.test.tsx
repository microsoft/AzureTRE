import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { render } from "../../../test-utils";
import { Airlock } from "./Airlock";
import { WorkspaceRoleName } from "../../../models/roleNames";

const mockApiCall = vi.fn();
const refreshHook = vi.hoisted(() => ({ trigger: () => undefined as unknown }));

vi.mock("../../../hooks/useAuthApiCall", () => ({
  useAuthApiCall: () => mockApiCall,
  HttpMethod: { Get: "GET" },
}));

vi.mock("../../../hooks/useRefresh", () => ({
  useRefresh: (callback: () => unknown) => {
    refreshHook.trigger = callback;
    return callback;
  },
}));

vi.mock("../ExceptionLayout", () => ({
  ExceptionLayout: ({ e }: any) => <div role="alert">{e.userMessage}</div>,
}));

vi.mock("@fluentui/react", async (importOriginal) => {
  const actual: any = await importOriginal();
  return {
    ...actual,
    CommandBar: ({ items }: any) => (
      <div>
        {items.map((item: any) => (
          <button key={item.key} onClick={item.onClick}>
            {item.text}
          </button>
        ))}
      </div>
    ),
    ShimmeredDetailsList: ({ items }: any) => (
      <ul>
        {items.map((r: any) => (
          <li key={r.id}>{r.title}</li>
        ))}
      </ul>
    ),
  };
});

const workspaceContext = {
  roles: [WorkspaceRoleName.AirlockManager],
  costs: [],
  setCosts: vi.fn(),
  setRoles: vi.fn(),
  setWorkspace: vi.fn(),
  workspace: { id: "ws", properties: {} },
  workspaceApplicationIdURI: "scope",
};

const response = (title: string) => ({
  airlockRequests: [{ airlockRequest: { id: title, title, files: [] }, allowedUserActions: [] }],
});

const renderAirlock = () =>
  render(<Airlock />, {
    children: null,
    initialEntries: ["/workspaces/ws/requests"],
    workspaceContext: workspaceContext as any,
  });

describe("Airlock request list", () => {
  beforeEach(() => vi.clearAllMocks());

  it("keeps the rows when a refresh of the same query fails transiently", async () => {
    mockApiCall.mockResolvedValueOnce(response("First request"));
    renderAirlock();
    expect(await screen.findByText("First request")).toBeInTheDocument();

    mockApiCall.mockRejectedValueOnce({ status: 503 });
    await act(async () => {
      await refreshHook.trigger();
    });

    expect(screen.getByText("First request")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows an error instead of stale rows when a new filter's query fails", async () => {
    mockApiCall.mockResolvedValueOnce(response("First request"));
    renderAirlock();
    expect(await screen.findByText("First request")).toBeInTheDocument();

    mockApiCall.mockRejectedValueOnce({ status: 503 });
    fireEvent.click(screen.getByRole("button", { name: "Awaiting my review" }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Error fetching airlock requests"));
    expect(screen.queryByText("First request")).not.toBeInTheDocument();
    expect(mockApiCall).toHaveBeenLastCalledWith(expect.stringContaining("status=in_review"), "GET", "scope");
  });
});

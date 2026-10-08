import React from "react";
import { act, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RequestsList } from "./RequestsList";
import { Airlock } from "./airlock/Airlock";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";

const mocks = vi.hoisted(() => ({
  apiCall: vi.fn(),
  refresh: undefined as (() => void) | undefined,
}));
vi.mock("../../hooks/useAuthApiCall", () => ({
  useAuthApiCall: () => mocks.apiCall,
  HttpMethod: { Get: "GET" },
}));
vi.mock("../../hooks/useRefresh", () => ({
  useRefresh: (callback: () => void) => {
    mocks.refresh = callback;
    return callback;
  },
}));
vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ accounts: [] }),
  useAccount: () => null,
}));
vi.mock("@fluentui/react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@fluentui/react")>();
  const { createCompleteFluentUIMock } = await import("../../test-utils/fluentui-mocks");
  return {
    ...actual,
    ...createCompleteFluentUIMock(),
    CommandBar: () => null,
    CommandBarButton: () => null,
    ShimmeredDetailsList: ({ enableShimmer, items }: any) => (
      <div data-testid="requests" data-loading={enableShimmer}>
        {items.length} requests
      </div>
    ),
  };
});
vi.mock("./airlock/AirlockViewRequest", () => ({ AirlockViewRequest: () => null }));
vi.mock("./airlock/AirlockNewRequest", () => ({ AirlockNewRequest: () => null }));
vi.mock("./ExceptionLayout", () => ({ ExceptionLayout: () => <span>Request error</span> }));

const context = {
  workspace: { id: "workspace" },
  workspaceApplicationIdURI: "scope",
  roles: [],
  costs: [],
  setCosts: vi.fn(),
  setRoles: vi.fn(),
  setWorkspace: vi.fn(),
};

describe.each([
  ["TRE", RequestsList],
  ["Workspace", Airlock],
] as const)("%s requests refresh", (_name, Component) => {
  beforeEach(() => {
    mocks.apiCall.mockReset();
    mocks.apiCall.mockImplementation(async (path: string) => {
      if (path === "workspaces") return { workspaces: [] };
      if (path.includes("/airlock")) return { airlockRequests: [] };
      return [];
    });
  });

  it("only shows a shimmer during the initial load, not during polling", async () => {
    render(
      <WorkspaceContext.Provider value={context as any}>
        <MemoryRouter>
          <Component />
        </MemoryRouter>
      </WorkspaceContext.Provider>,
    );
    expect(screen.getByTestId("requests")).toHaveAttribute("data-loading", "true");
    await act(async () => {});
    expect(screen.getByTestId("requests")).toHaveAttribute("data-loading", "false");

    let resolve!: (value: any) => void;
    mocks.apiCall.mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done;
        }),
    );
    act(() => {
      mocks.refresh!();
    });
    expect(screen.getByTestId("requests")).toHaveAttribute("data-loading", "false");

    await act(async () => resolve(_name === "TRE" ? { workspaces: [] } : { airlockRequests: [] }));
    expect(screen.getByTestId("requests")).toHaveAttribute("data-loading", "false");
  });
});

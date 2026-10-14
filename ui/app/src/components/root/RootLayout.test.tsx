import React from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RootLayout } from "./RootLayout";
import { AppRolesContext } from "../../contexts/AppRolesContext";
import { CostsContext } from "../../contexts/CostsContext";
import { RoleName } from "../../models/roleNames";
import { LoadingState } from "../../models/loadingState";
import { APIError } from "../../models/exceptions";

const apiCall = vi.hoisted(() => vi.fn());
vi.mock("../../hooks/useAuthApiCall", () => ({
  useAuthApiCall: () => apiCall,
  HttpMethod: { Get: "GET" },
  ResultType: { JSON: "JSON" },
}));
vi.mock("../../hooks/useRefresh", () => ({ useRefresh: (callback: () => void) => callback }));
vi.mock("@fluentui/react", async () => {
  const { createCompleteFluentUIMock } = await import("../../test-utils/fluentui-mocks");
  return createCompleteFluentUIMock();
});
vi.mock("../../App", () => ({ Admin: () => null }));
vi.mock("./LeftNav", () => ({ LeftNav: () => null }));
vi.mock("../shared/SharedServices", () => ({ SharedServices: () => null }));
vi.mock("../shared/SharedServiceItem", () => ({ SharedServiceItem: () => null }));
vi.mock("../shared/RequestsList", () => ({ RequestsList: () => null }));
vi.mock("../shared/ExceptionLayout", () => ({
  ExceptionLayout: ({ onRetry }: any) => <button onClick={onRetry}>Retry</button>,
}));
vi.mock("./RootDashboard", () => ({
  RootDashboard: ({ workspaces, onRefresh }: any) => (
    <>
      <span>{workspaces.length} workspaces</span>
      <button onClick={onRefresh}>Refresh</button>
    </>
  ),
}));

describe("RootLayout refresh", () => {
  beforeEach(() => apiCall.mockReset());

  it("preserves the workspace list after a background refresh fails", async () => {
    apiCall.mockResolvedValueOnce({ workspaces: [{ id: "workspace" }] });
    render(
      <MemoryRouter>
        <RootLayout />
      </MemoryRouter>,
    );
    expect(await screen.findByText("1 workspaces")).toBeInTheDocument();

    apiCall.mockRejectedValueOnce({ status: 503 });
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Refresh" })));
    expect(screen.getByText("1 workspaces")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
  });

  it("shows an initial-load error and supports retry", async () => {
    apiCall.mockRejectedValueOnce({ status: 503 });
    render(
      <MemoryRouter>
        <RootLayout />
      </MemoryRouter>,
    );
    await screen.findByRole("button", { name: "Retry" });

    apiCall.mockResolvedValueOnce({ workspaces: [] });
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Retry" })));
    expect(screen.getByText("0 workspaces")).toBeInTheDocument();
  });

  it("does not retain the loaded view when authorization fails", async () => {
    apiCall.mockResolvedValueOnce({ workspaces: [] });
    render(
      <MemoryRouter>
        <RootLayout />
      </MemoryRouter>,
    );
    await screen.findByText("0 workspaces");

    apiCall.mockRejectedValueOnce({ status: 403 });
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Refresh" })));
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("does not retain the loaded view for a terminal error", async () => {
    apiCall.mockResolvedValueOnce({ workspaces: [] });
    render(
      <MemoryRouter>
        <RootLayout />
      </MemoryRouter>,
    );
    await screen.findByText("0 workspaces");

    apiCall.mockRejectedValueOnce({ status: 404 });
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Refresh" })));
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});

describe("RootLayout costs", () => {
  beforeEach(() => apiCall.mockReset());

  const renderAsAdmin = (costs: any) =>
    render(
      <AppRolesContext.Provider value={{ roles: [RoleName.TREAdmin], setAppRoles: vi.fn() }}>
        <CostsContext.Provider value={costs}>
          <MemoryRouter>
            <RootLayout />
          </MemoryRouter>
        </CostsContext.Provider>
      </AppRolesContext.Provider>,
    );

  it("keeps costs loading while a server-requested retry is pending, then loads them", async () => {
    vi.useFakeTimers();
    try {
      const costs = { costs: [], loadingState: LoadingState.Loading, setCosts: vi.fn(), setLoadingState: vi.fn() };
      const throttled = new APIError();
      throttled.status = 429;
      throttled.message = JSON.stringify({ error: { "retry-after": 5 } });
      apiCall.mockImplementation(async (endpoint: string) => {
        if (endpoint === "costs") {
          if (apiCall.mock.calls.filter((c) => c[0] === "costs").length === 1) throw throttled;
          return { workspaces: [], shared_services: [] };
        }
        return { workspaces: [] };
      });

      renderAsAdmin(costs);
      await act(async () => {});
      expect(costs.setLoadingState).not.toHaveBeenCalledWith(LoadingState.NotSupported);

      await act(async () => vi.advanceTimersByTime(5000));
      expect(costs.setLoadingState).toHaveBeenLastCalledWith(LoadingState.Ok);
      expect(costs.setLoadingState).not.toHaveBeenCalledWith(LoadingState.NotSupported);
    } finally {
      vi.useRealTimers();
    }
  });

  it("retries a transient cost failure without retry-after instead of marking costs unsupported", async () => {
    vi.useFakeTimers();
    try {
      const costs = { costs: [], loadingState: LoadingState.Loading, setCosts: vi.fn(), setLoadingState: vi.fn() };
      const unavailable = new APIError();
      unavailable.status = 503;
      unavailable.message = "Failed to fetch";
      apiCall.mockImplementation(async (endpoint: string) => {
        if (endpoint === "costs") {
          if (apiCall.mock.calls.filter((c) => c[0] === "costs").length === 1) throw unavailable;
          return { workspaces: [], shared_services: [] };
        }
        return { workspaces: [] };
      });

      renderAsAdmin(costs);
      await act(async () => {});
      expect(costs.setLoadingState).not.toHaveBeenCalledWith(LoadingState.NotSupported);

      await act(async () => vi.advanceTimersByTime(5000));
      expect(costs.setLoadingState).toHaveBeenLastCalledWith(LoadingState.Ok);
    } finally {
      vi.useRealTimers();
    }
  });

  it("only marks costs unsupported for a 404", async () => {
    const costs = { costs: [], loadingState: LoadingState.Loading, setCosts: vi.fn(), setLoadingState: vi.fn() };
    const forbidden = new APIError();
    forbidden.status = 403;
    apiCall.mockImplementation(async (endpoint: string) => {
      if (endpoint === "costs") throw forbidden;
      return { workspaces: [] };
    });

    renderAsAdmin(costs);
    await act(async () => {});
    expect(costs.setLoadingState).toHaveBeenLastCalledWith(LoadingState.Error);
    expect(costs.setLoadingState).not.toHaveBeenCalledWith(LoadingState.NotSupported);
  });
});

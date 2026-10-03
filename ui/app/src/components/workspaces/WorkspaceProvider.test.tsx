import React from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { WorkspaceProvider } from "./WorkspaceProvider";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { RoleName, WorkspaceRoleName } from "../../models/roleNames";
import { AppRolesContext } from "../../contexts/AppRolesContext";

const apiCall = vi.hoisted(() => vi.fn());
vi.mock("../../hooks/useAuthApiCall", () => ({
  useAuthApiCall: () => apiCall,
  HttpMethod: { Get: "GET" },
  ResultType: { JSON: "JSON" },
}));
vi.mock("@fluentui/react", async () => {
  const { createCompleteFluentUIMock } = await import("../../test-utils/fluentui-mocks");
  return createCompleteFluentUIMock();
});
vi.mock("./WorkspaceHeader", () => ({ WorkspaceHeader: () => <span>Loaded workspace</span> }));
vi.mock("./WorkspaceLeftNav", () => ({ WorkspaceLeftNav: () => null }));
vi.mock("./WorkspaceItem", () => ({
  WorkspaceItem: ({ onRefresh }: any) => <button onClick={onRefresh}>Refresh</button>,
}));
vi.mock("./WorkspaceServices", () => ({ WorkspaceServices: () => null }));
vi.mock("./WorkspaceServiceItem", () => ({ WorkspaceServiceItem: () => null }));
vi.mock("./WorkspaceUsers", () => ({ WorkspaceUsers: () => null }));
vi.mock("../shared/SharedServices", () => ({ SharedServices: () => null }));
vi.mock("../shared/SharedServiceItem", () => ({ SharedServiceItem: () => null }));
vi.mock("../shared/airlock/Airlock", () => ({ Airlock: () => null }));
vi.mock("../shared/ExceptionLayout", () => ({
  ExceptionLayout: ({ onRetry }: any) => <button onClick={onRetry}>Retry</button>,
}));

const context = {
  workspace: { id: "" },
  workspaceApplicationIdURI: "",
  roles: [],
  costs: [],
  setWorkspace: vi.fn(),
  setRoles: vi.fn(),
  setCosts: vi.fn(),
};
const workspace = (id: string) => ({ id, properties: { scope_id: "scope" } });
const Navigate = () => {
  const navigate = useNavigate();
  return <button onClick={() => navigate("/workspaces/second")}>Next workspace</button>;
};
const renderWorkspace = () =>
  render(
    <WorkspaceContext.Provider value={context as any}>
      <MemoryRouter initialEntries={["/workspaces/first"]}>
        <Navigate />
        <Routes>
          <Route path="/workspaces/:workspaceId/*" element={<WorkspaceProvider />} />
        </Routes>
      </MemoryRouter>
    </WorkspaceContext.Provider>,
  );

describe("WorkspaceProvider refresh", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  beforeEach(() => {
    vi.clearAllMocks();
    apiCall.mockReset();
    apiCall.mockImplementation(async (path: string, _method: any, _scope: any, _body: any, _type: any, roles: any) => {
      if (path.endsWith("/scopeid")) return { workspaceAuth: { scopeId: "scope" } };
      if (roles) {
        roles([WorkspaceRoleName.WorkspaceResearcher]);
        return;
      }
      if (path.endsWith("/workspace-services")) return { workspaceServices: [] };
      if (path === "shared-services") return { sharedServices: [] };
      return { workspace: workspace(path.split("/").pop()!) };
    });
  });

  it("keeps the loaded workspace after a transient refresh failure", async () => {
    renderWorkspace();
    await screen.findByText("Loaded workspace");
    const calls = context.setWorkspace.mock.calls.length;
    apiCall.mockRejectedValueOnce({ status: 503 });

    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Refresh" })));
    expect(screen.getByText("Loaded workspace")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
    expect(context.setWorkspace).toHaveBeenCalledTimes(calls);
  });

  it("keeps the loaded workspace when token acquisition fails during a refresh", async () => {
    renderWorkspace();
    await screen.findByText("Loaded workspace");
    const calls = context.setRoles.mock.calls.length;
    const base = apiCall.getMockImplementation()!;
    apiCall.mockImplementation(async (...args: any[]) => {
      if (args[5]) throw new Error("interaction_required");
      return base(...args);
    });

    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Refresh" })));
    expect(screen.getByText("Loaded workspace")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
    expect(context.setRoles).toHaveBeenCalledTimes(calls);
  });

  it("loads shared services for a TRE Admin who is also a workspace researcher", async () => {
    render(
      <AppRolesContext.Provider value={{ roles: [RoleName.TREAdmin], setAppRoles: vi.fn() }}>
        <WorkspaceContext.Provider value={context as any}>
          <MemoryRouter initialEntries={["/workspaces/first"]}>
            <Routes>
              <Route path="/workspaces/:workspaceId/*" element={<WorkspaceProvider />} />
            </Routes>
          </MemoryRouter>
        </WorkspaceContext.Provider>
      </AppRolesContext.Provider>,
    );
    await screen.findByText("Loaded workspace");
    expect(apiCall).toHaveBeenCalledWith("shared-services", "GET");
  });

  it("shows an error when a refresh finds the workspace has been deleted", async () => {
    renderWorkspace();
    await screen.findByText("Loaded workspace");
    apiCall.mockRejectedValueOnce({ status: 404 });

    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Refresh" })));
    expect(await screen.findByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(screen.queryByText("Loaded workspace")).not.toBeInTheDocument();
  });

  it("shows an error for a failed initial load", async () => {
    apiCall.mockRejectedValueOnce({ status: 503 });
    renderWorkspace();
    expect(await screen.findByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("coalesces refreshes while a workspace load is pending", async () => {
    renderWorkspace();
    await screen.findByText("Loaded workspace");
    let resolveOld!: (result: any) => void;
    apiCall.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveOld = resolve;
        }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    const apiCalls = apiCall.mock.calls.length;
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Refresh" })));
    expect(apiCall).toHaveBeenCalledTimes(apiCalls);
    const calls = context.setWorkspace.mock.calls.length;

    await act(async () => resolveOld({ workspaceAuth: { scopeId: "old-scope" } }));
    expect(context.setWorkspace).toHaveBeenCalledTimes(calls + 1);
    expect(context.setWorkspace).toHaveBeenLastCalledWith(workspace("first"));
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Refresh" })));
    expect(context.setWorkspace).toHaveBeenCalledTimes(calls + 2);
  });

  it("allows an initial load spanning multiple polling intervals to complete", async () => {
    vi.useFakeTimers();
    vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
    let finish!: (result: any) => void;
    apiCall.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    renderWorkspace();

    act(() => vi.advanceTimersByTime(90000));
    expect(apiCall).toHaveBeenCalledOnce();

    await act(async () => finish({ workspaceAuth: { scopeId: "scope" } }));
    expect(screen.getByText("Loaded workspace")).toBeInTheDocument();
    expect(context.setWorkspace).toHaveBeenLastCalledWith(workspace("first"));
  });

  it("ignores a previous workspace response after navigation", async () => {
    renderWorkspace();
    await screen.findByText("Loaded workspace");
    let resolveOld!: (result: any) => void;
    apiCall.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveOld = resolve;
        }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Next workspace" })));
    expect(context.setWorkspace).toHaveBeenLastCalledWith(workspace("second"));
    const roleCalls = context.setRoles.mock.calls.length;

    await act(async () => resolveOld({ workspaceAuth: { scopeId: "old-scope" } }));
    expect(context.setWorkspace).toHaveBeenLastCalledWith(workspace("second"));
    expect(context.setRoles).toHaveBeenCalledTimes(roleCalls);
  });

  it.each(["success", "failure"])("ignores an obsolete service %s after navigation", async (result) => {
    renderWorkspace();
    await screen.findByText("Loaded workspace");
    const defaultCall = apiCall.getMockImplementation()!;
    let finish!: () => void;
    apiCall
      .mockImplementationOnce(defaultCall)
      .mockImplementationOnce(defaultCall)
      .mockImplementationOnce(defaultCall)
      .mockImplementationOnce(
        () =>
          new Promise((resolve, reject) => {
            finish = () =>
              result === "success"
                ? resolve({ workspaceServices: [{ id: "obsolete-service" }] })
                : reject({ status: 403 });
          }),
      );

    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Refresh" })));
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Next workspace" })));
    const calls = context.setWorkspace.mock.calls.length;

    await act(async () => finish());
    expect(context.setWorkspace).toHaveBeenCalledTimes(calls);
    expect(context.setWorkspace).toHaveBeenLastCalledWith(workspace("second"));
    expect(screen.getByText("Loaded workspace")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
  });
});

import React from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { WorkspaceProvider } from "./WorkspaceProvider";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { WorkspaceRoleName } from "../../models/roleNames";

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

  it("shows an error for a failed initial load", async () => {
    apiCall.mockRejectedValueOnce({ status: 503 });
    renderWorkspace();
    expect(await screen.findByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("ignores an obsolete refresh response that finishes after a newer response", async () => {
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
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Refresh" })));
    const calls = context.setWorkspace.mock.calls.length;

    await act(async () => resolveOld({ workspaceAuth: { scopeId: "old-scope" } }));
    expect(context.setWorkspace).toHaveBeenCalledTimes(calls);
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

  it.each(["success", "failure"])("ignores an obsolete service %s after a newer refresh completes", async (result) => {
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
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Refresh" })));
    const calls = context.setWorkspace.mock.calls.length;

    await act(async () => finish());
    expect(context.setWorkspace).toHaveBeenCalledTimes(calls);
    expect(screen.getByText("Loaded workspace")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
  });
});

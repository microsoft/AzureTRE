import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { Link, Route, Routes } from "react-router-dom";
import { render } from "../../test-utils";
import { UserResource } from "../../models/userResource";
import { UserResourceItem } from "./UserResourceItem";

const mockApiCall = vi.fn();

vi.mock("../../hooks/useAuthApiCall", () => ({
  useAuthApiCall: () => mockApiCall,
  HttpMethod: { Get: "GET" },
}));

vi.mock("../../hooks/useComponentManager", () => ({
  useComponentManager: () => ({ componentAction: "none", operation: {} }),
}));

vi.mock("../../hooks/useRefresh", () => ({
  useRefresh: (onRefresh: () => void) => onRefresh,
}));

vi.mock("../shared/ResourceHeader", () => ({
  ResourceHeader: ({ resource, onRefresh }: any) => (
    <div>
      <span data-testid="power-state">{resource.azureStatus?.powerState}</span>
      <button onClick={onRefresh}>Refresh</button>
    </div>
  ),
}));

vi.mock("../shared/ResourceBody", () => ({
  ResourceBody: () => null,
}));

vi.mock("../shared/ExceptionLayout", () => ({
  ExceptionLayout: ({ e, onRetry }: any) => (
    <div>
      <span>{e.status}</span>
      <button onClick={onRetry}>Retry</button>
    </div>
  ),
}));

const userResource = {
  id: "test-user-resource",
  resourceType: "user-resource",
  resourcePath: "/workspaces/test-workspace/workspace-services/test-service/user-resources/test-user-resource",
  azureStatus: { powerState: "VM running" },
} as UserResource;

const workspaceContext = {
  roles: [],
  costs: [],
  setCosts: vi.fn(),
  setRoles: vi.fn(),
  setWorkspace: vi.fn(),
  workspace: { id: "test-workspace" },
  workspaceApplicationIdURI: "test-app-id-uri",
};

describe("UserResourceItem", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("uses the passed resource initially and fetches it again on refresh", async () => {
    mockApiCall.mockResolvedValue({ userResource: { ...userResource, azureStatus: { powerState: "VM stopped" } } });

    render(
      <Routes>
        <Route
          path="/workspaces/:workspaceServiceId/user-resources/:userResourceId"
          element={
            <UserResourceItem userResource={userResource} updateUserResource={vi.fn()} removeUserResource={vi.fn()} />
          }
        />
      </Routes>,
      {
        children: null,
        initialEntries: ["/workspaces/test-service/user-resources/test-user-resource"],
        workspaceContext: workspaceContext as any,
      },
    );

    expect(screen.getByTestId("power-state")).toHaveTextContent("VM running");
    expect(mockApiCall).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));

    await waitFor(() => {
      expect(mockApiCall).toHaveBeenCalledOnce();
      expect(screen.getByTestId("power-state")).toHaveTextContent("VM stopped");
    });
  });

  it("keeps the last resource visible when a refresh fails", async () => {
    mockApiCall.mockRejectedValueOnce({ status: 503 });

    render(
      <Routes>
        <Route
          path="/workspaces/:workspaceServiceId/user-resources/:userResourceId"
          element={
            <UserResourceItem userResource={userResource} updateUserResource={vi.fn()} removeUserResource={vi.fn()} />
          }
        />
      </Routes>,
      {
        children: null,
        initialEntries: ["/workspaces/test-service/user-resources/test-user-resource"],
        workspaceContext: workspaceContext as any,
      },
    );

    expect(screen.getByTestId("power-state")).toHaveTextContent("VM running");
    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));

    await waitFor(() => expect(mockApiCall).toHaveBeenCalledOnce());
    expect(screen.getByTestId("power-state")).toHaveTextContent("VM running");
  });

  it("shows an error and retries when the initial direct load fails", async () => {
    mockApiCall
      .mockRejectedValueOnce({ status: 503 })
      .mockResolvedValueOnce({ userResource: { ...userResource, azureStatus: { powerState: "VM stopped" } } });

    render(
      <Routes>
        <Route
          path="/workspaces/:workspaceServiceId/user-resources/:userResourceId"
          element={<UserResourceItem updateUserResource={vi.fn()} removeUserResource={vi.fn()} />}
        />
      </Routes>,
      {
        children: null,
        initialEntries: ["/workspaces/test-service/user-resources/test-user-resource"],
        workspaceContext: workspaceContext as any,
      },
    );

    expect(await screen.findByText("503")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    await waitFor(() => expect(screen.getByTestId("power-state")).toHaveTextContent("VM stopped"));
    expect(mockApiCall).toHaveBeenCalledTimes(2);
  });

  it("does not show a previously loaded resource when the route changes and the new load fails", async () => {
    mockApiCall.mockRejectedValueOnce({ status: 503 });

    render(
      <Routes>
        <Route
          path="/workspaces/:workspaceServiceId/user-resources/:userResourceId"
          element={
            <>
              <Link to="/workspaces/test-service/user-resources/another-user-resource">Another resource</Link>
              <UserResourceItem userResource={userResource} updateUserResource={vi.fn()} removeUserResource={vi.fn()} />
            </>
          }
        />
      </Routes>,
      {
        children: null,
        initialEntries: ["/workspaces/test-service/user-resources/test-user-resource"],
        workspaceContext: workspaceContext as any,
      },
    );

    expect(screen.getByTestId("power-state")).toHaveTextContent("VM running");
    fireEvent.click(screen.getByRole("link", { name: "Another resource" }));

    expect(await screen.findByText("503")).toBeInTheDocument();
    expect(screen.queryByTestId("power-state")).not.toBeInTheDocument();
    expect(mockApiCall).toHaveBeenCalledOnce();
  });

  it("ignores a slower response for the previous route", async () => {
    const other = { ...userResource, id: "another-user-resource", azureStatus: { powerState: "VM deallocated" } };
    let resolveFirst: (value: any) => void = () => undefined;
    mockApiCall
      .mockImplementationOnce(() => new Promise((resolve) => (resolveFirst = resolve)))
      .mockResolvedValueOnce({ userResource: other });

    render(
      <Routes>
        <Route
          path="/workspaces/:workspaceServiceId/user-resources/:userResourceId"
          element={
            <>
              <Link to="/workspaces/test-service/user-resources/another-user-resource">Another resource</Link>
              <UserResourceItem userResource={userResource} updateUserResource={vi.fn()} removeUserResource={vi.fn()} />
            </>
          }
        />
      </Routes>,
      {
        children: null,
        initialEntries: ["/workspaces/test-service/user-resources/test-user-resource"],
        workspaceContext: workspaceContext as any,
      },
    );

    // Refresh resource A, then navigate to B before A's request finishes.
    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    fireEvent.click(screen.getByRole("link", { name: "Another resource" }));
    await waitFor(() => expect(screen.getByTestId("power-state")).toHaveTextContent("VM deallocated"));

    resolveFirst({ userResource });
    await new Promise((r) => setTimeout(r, 0));
    expect(screen.getByTestId("power-state")).toHaveTextContent("VM deallocated");
  });

  it("replaces the stale resource with the error when a refresh returns a terminal error", async () => {
    mockApiCall.mockRejectedValueOnce({ status: 404 });

    render(
      <Routes>
        <Route
          path="/workspaces/:workspaceServiceId/user-resources/:userResourceId"
          element={
            <UserResourceItem userResource={userResource} updateUserResource={vi.fn()} removeUserResource={vi.fn()} />
          }
        />
      </Routes>,
      {
        children: null,
        initialEntries: ["/workspaces/test-service/user-resources/test-user-resource"],
        workspaceContext: workspaceContext as any,
      },
    );

    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));

    expect(await screen.findByText("404")).toBeInTheDocument();
    expect(screen.queryByTestId("power-state")).not.toBeInTheDocument();
  });
});

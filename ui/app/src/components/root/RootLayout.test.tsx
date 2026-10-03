import React from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RootLayout } from "./RootLayout";

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

import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { SharedServices } from "./SharedServices";

const { mockApiCall } = vi.hoisted(() => ({ mockApiCall: vi.fn() }));

vi.mock("../../hooks/useAuthApiCall", () => ({
  HttpMethod: { Get: "GET" },
  useAuthApiCall: () => mockApiCall,
}));

vi.mock("../../hooks/useRefresh", () => ({
  useRefresh: (onRefresh: () => void) => onRefresh,
}));

vi.mock("./ResourceListControls", () => ({
  defaultSortOptions: () => [],
  ResourceListControls: () => null,
  useResourceListFilter: (resources: Array<{ id: string }>) => ({ visibleResources: resources, controlsProps: {} }),
}));

vi.mock("./ResourceCardList", () => ({
  ResourceCardList: ({ resources }: { resources: Array<{ id: string }> }) => (
    <div>
      {resources.map((resource) => (
        <span key={resource.id}>{resource.id}</span>
      ))}
    </div>
  ),
}));

vi.mock("./RefreshButton", () => ({
  RefreshButton: ({ onClick }: { onClick: () => void }) => <button onClick={onClick}>Refresh</button>,
}));

vi.mock("./SecuredByRole", () => ({
  SecuredByRole: ({ element }: { element: React.ReactNode }) => element,
}));

vi.mock("./ExceptionLayout", () => ({
  ExceptionLayout: ({ e, onRetry }: any) => (
    <div>
      <span>{e.userMessage}</span>
      <button onClick={onRetry}>Retry</button>
    </div>
  ),
}));

describe("SharedServices", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows retryable initial-load errors and retries the request", async () => {
    mockApiCall
      .mockRejectedValueOnce({
        status: 503,
        userMessage: "The TRE API is currently unavailable. Please try again later or contact your administrator.",
      })
      .mockResolvedValueOnce({ sharedServices: [] });
    render(<SharedServices />);

    const unavailableMessage =
      "The TRE API is currently unavailable. Please try again later or contact your administrator.";
    expect(await screen.findByText(unavailableMessage)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    await waitFor(() => expect(mockApiCall).toHaveBeenCalledTimes(2));
    await waitFor(() => {
      expect(screen.queryByText(unavailableMessage)).not.toBeInTheDocument();
    });
  });

  it("ignores stale responses from overlapping list refreshes", async () => {
    let resolveFirstRefresh: (response: { sharedServices: Array<{ id: string }> }) => void = () => {};
    let resolveSecondRefresh: (response: { sharedServices: Array<{ id: string }> }) => void = () => {};
    mockApiCall
      .mockResolvedValueOnce({ sharedServices: [{ id: "initial" }] })
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveFirstRefresh = resolve;
          }),
      )
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveSecondRefresh = resolve;
          }),
      );

    render(<SharedServices />);
    expect(await screen.findByText("initial")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    await waitFor(() => expect(mockApiCall).toHaveBeenCalledTimes(2));
    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    await waitFor(() => expect(mockApiCall).toHaveBeenCalledTimes(3));

    await act(async () => {
      resolveSecondRefresh({ sharedServices: [{ id: "newer" }] });
    });
    expect(await screen.findByText("newer")).toBeInTheDocument();

    await act(async () => {
      resolveFirstRefresh({ sharedServices: [{ id: "older" }] });
    });
    expect(screen.getByText("newer")).toBeInTheDocument();
    expect(screen.queryByText("older")).not.toBeInTheDocument();
  });
});

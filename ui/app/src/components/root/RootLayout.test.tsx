import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "../../test-utils";
import { RootLayout } from "./RootLayout";

const mockApiCall = vi.fn();

vi.mock("../../hooks/useAuthApiCall", () => ({
  useAuthApiCall: () => mockApiCall,
  HttpMethod: { Get: "GET" },
  ResultType: { JSON: "json" },
}));

vi.mock("./RootDashboard", () => ({
  RootDashboard: () => <div>Root Dashboard</div>,
}));

vi.mock("./LeftNav", () => ({
  LeftNav: () => <div>Left Nav</div>,
}));

vi.mock("../shared/RequestsList", () => ({
  RequestsList: () => <div>Requests List</div>,
}));

vi.mock("../shared/SharedServices", () => ({
  SharedServices: () => <div>Shared Services</div>,
}));

vi.mock("../shared/SharedServiceItem", () => ({
  SharedServiceItem: () => <div>Shared Service Item</div>,
}));

vi.mock("../shared/SecuredByRole", () => ({
  SecuredByRole: ({ element }: { element: React.ReactElement }) => element,
}));

describe("RootLayout routes", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiCall.mockResolvedValue({ workspaces: [] });
  });

  it("renders root dashboard on home route", async () => {
    render(<RootLayout />, {
      children: <></>,
      initialEntries: ["/"],
      appRolesContext: { roles: [], setAppRoles: vi.fn() },
    });

    await waitFor(() => {
      expect(screen.getByText("Root Dashboard")).toBeInTheDocument();
    });
  });

  it("renders a 404 page for an unknown route", async () => {
    render(<RootLayout />, {
      children: <></>,
      initialEntries: ["/does-not-exist"],
      appRolesContext: { roles: [], setAppRoles: vi.fn() },
    });

    await waitFor(() => {
      expect(screen.getByText("404 - Page not found")).toBeInTheDocument();
    });

    expect(screen.getByRole("link", { name: "Go to home page" })).toHaveAttribute("href", "/");
  });
});

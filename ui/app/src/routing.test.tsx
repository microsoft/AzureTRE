import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Link, MemoryRouter, useLocation, useNavigate, useParams } from "react-router-dom";
import { App } from "./App";

const { apiCall } = vi.hoisted(() => ({ apiCall: vi.fn() }));

vi.mock("./config.json", () => ({ default: { debug: false, userManagementEnabled: true } }));

vi.mock("./hooks/useAuthApiCall", () => ({
  useAuthApiCall: () => apiCall,
  HttpMethod: { Get: "GET", Post: "POST", Patch: "PATCH", Delete: "DELETE" },
  ResultType: { JSON: "JSON" },
}));
vi.mock("./hooks/useComponentManager", () => ({ useComponentManager: () => ({}) }));
vi.mock("./components/shared/TopNav", () => ({
  TopNav: () => <Link to="/">Home</Link>,
}));
vi.mock("./components/shared/Footer", () => ({ Footer: () => null }));
vi.mock("./components/shared/create-update-resource/CreateUpdateResource", () => ({
  CreateUpdateResource: () => null,
}));
// Keep App and every nested Routes owner real. Replace resource display widgets,
// authentication (in setupTests) and API calls with deterministic fixtures.
vi.mock("./components/root/RootDashboard", () => ({
  RootDashboard: () => <Link to="/workspaces/workspace">Open workspace</Link>,
}));
vi.mock("./components/workspaces/WorkspaceHeader", () => ({ WorkspaceHeader: () => null }));
vi.mock("./components/workspaces/WorkspaceItem", () => ({
  WorkspaceItem: () => <h1>Workspace overview</h1>,
}));
vi.mock("./components/workspaces/WorkspaceServices", () => ({
  WorkspaceServices: () => <h2>Workspace services</h2>,
}));
vi.mock("./components/shared/SharedServices", () => ({
  SharedServices: () => <h1>Shared services</h1>,
}));
vi.mock("./components/shared/SharedServiceItem", () => ({
  SharedServiceItem: () => <h1>Shared service {useParams().sharedServiceId}</h1>,
}));
vi.mock("./components/shared/ResourceHeader", () => ({
  ResourceHeader: ({ resource }: { resource: { id: string } }) => <h1>Service {resource.id}</h1>,
}));
vi.mock("./components/shared/ResourceBody", () => ({ ResourceBody: () => null }));
vi.mock("./components/shared/ResourceCardList", () => ({ ResourceCardList: () => null }));
vi.mock("./components/workspaces/UserResourceItem", () => ({
  UserResourceItem: () => <h1>User resource {useParams().userResourceId}</h1>,
}));

const workspace = {
  id: "workspace",
  templateName: "tre-workspace-base",
  templateVersion: "2.10.1",
  deploymentStatus: "deployed",
  properties: { display_name: "Research", scope_id: "api://workspace", enable_airlock: true, create_aad_groups: true },
};
const service = {
  id: "service",
  templateName: "tre-workspace-service-guacamole",
  properties: { display_name: "Desktop service" },
};
const request = {
  id: "request",
  workspaceId: "workspace",
  title: "Existing request",
  type: "import",
  status: "draft",
  createdWhen: 0,
  updatedWhen: 0,
  allowedUserActions: [],
};

let listedRequests: Array<typeof request> = [];

const LocationControls = () => {
  const location = useLocation();
  const navigate = useNavigate();
  return (
    <>
      <output data-testid="location">{location.pathname + location.search + location.hash}</output>
      <button onClick={() => navigate(-1)}>History back</button>
      <button onClick={() => navigate(1)}>History forward</button>
    </>
  );
};

const open = (path: string) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <LocationControls />
      <App />
    </MemoryRouter>,
  );

beforeEach(() => {
  listedRequests = [];
  // Fluent UI constructs observers when its panels and command bars mount.
  class Observer {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  vi.stubGlobal("ResizeObserver", Observer);
  vi.stubGlobal("IntersectionObserver", Observer);
  apiCall.mockReset().mockImplementation(async (path, method, scope, _data, _result, roles, tokenOnly) => {
    if (method !== "GET") throw new Error("Unexpected mutation: " + method);
    if (tokenOnly) {
      roles?.(scope ? ["WorkspaceOwner"] : ["TREAdmin"]);
      return {};
    }
    const endpoint = path.replace(/^\//, "").split("?")[0];
    if (endpoint.endsWith("/scopeid")) return { workspaceAuth: { scopeId: "api://workspace" } };
    if (endpoint === "workspaces") return { workspaces: [workspace] };
    if (endpoint === "workspaces/workspace") return { workspace };
    if (endpoint.endsWith("/costs") || endpoint === "costs")
      return { costs: [], workspace_services: [], workspaces: [], shared_services: [] };
    if (endpoint === "shared-services") return { sharedServices: [] };
    if (endpoint.endsWith("/workspace-services")) return { workspaceServices: [service] };
    if (endpoint.endsWith("/workspace-services/service")) return { workspaceService: service };
    if (endpoint.endsWith("/user-resources")) return { userResources: [] };
    if (endpoint.endsWith("/user-resource-templates")) return { templates: [] };
    if (endpoint.endsWith("/users")) return { users: [] };
    if (endpoint.endsWith("/roles")) return { roles: [] };
    if (endpoint.endsWith("/requests")) {
      return { airlockRequests: listedRequests.map((r) => ({ airlockRequest: r, allowedUserActions: [] })) };
    }
    const selectedRequest = [request, ...listedRequests].find(
      (r) => endpoint === `workspaces/${r.workspaceId}/requests/${r.id}`,
    );
    if (selectedRequest) return { airlockRequest: selectedRequest, allowedUserActions: [] };
    throw new Error("Unexpected API path: " + endpoint);
  });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  expect(apiCall.mock.calls.every((call) => call[1] === "GET")).toBe(true);
});

describe("application navigation with the real router", () => {
  it.each([
    ["/workspaces/workspace", "Workspace overview"],
    ["/workspaces/workspace/", "Workspace overview"],
    ["/workspaces/workspace/workspace-services", "Workspace services"],
    ["/workspaces/workspace/workspace-services/service", "Service service"],
    ["/workspaces/workspace/workspace-services/service/user-resources/desktop", "User resource desktop"],
    ["/workspaces/workspace/shared-services/shared", "Shared service shared"],
    ["/shared-services", "Shared services"],
    ["/shared-services/shared", "Shared service shared"],
    ["/workspaces/workspace/users", "Users"],
    ["/logout", "You are logged out."],
  ])("opens the bookmarked route %s", async (path, heading) => {
    open(path);
    expect(await screen.findByRole("heading", { name: heading })).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent(path);
  });

  it("preserves navigation through the workspace menu and browser history", async () => {
    open("/");
    fireEvent.click(await screen.findByRole("link", { name: "Open workspace" }));
    await screen.findByRole("heading", { name: "Workspace overview" });
    fireEvent.click(await screen.findByRole("link", { name: "Services" }));
    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent("/workspaces/workspace/workspace-services"),
    );
    fireEvent.click(screen.getByRole("button", { name: "History back" }));
    await screen.findByRole("heading", { name: "Workspace overview" });
    fireEvent.click(screen.getByRole("button", { name: "History forward" }));
    await screen.findByRole("heading", { name: "Workspace services" });
    fireEvent.click(screen.getByRole("link", { name: "Home" }));
    await screen.findByRole("link", { name: "Open workspace" });
  });

  it.each([
    ["/workspaces/workspace/requests", "New request", "New airlock request"],
    ["/workspaces/workspace/users", "Assign New", "Assign users to a role"],
  ])("opens and dismisses a child panel from %s", async (parent, action, heading) => {
    open(parent);
    fireEvent.click(await screen.findByRole("button", { name: action }));
    await screen.findByText(heading);
    expect(screen.getByTestId("location").textContent).toBe(parent + "/new");
    fireEvent.click(
      screen
        .getAllByRole("button", { name: "Close" })
        .find((button) => button.classList.contains("ms-Panel-closeButton"))!,
    );
    await waitFor(() => expect(screen.getByTestId("location").textContent).toBe(parent + "/"));
    await waitFor(() => expect(screen.queryByText(heading)).not.toBeInTheDocument());
  });

  it.each([
    ["/workspaces/workspace/requests/new", "New airlock request", "/workspaces/workspace/requests/"],
    ["/workspaces/workspace/requests/request", "Existing request", "/workspaces/workspace/requests/"],
    ["/workspaces/workspace/users/new", "Assign users to a role", "/workspaces/workspace/users/"],
  ])("dismisses the bookmarked child panel %s to its parent", async (path, heading, parent) => {
    open(path);
    await screen.findByText(heading);
    fireEvent.click(
      screen
        .getAllByRole("button", { name: "Close" })
        .find((button) => button.classList.contains("ms-Panel-closeButton"))!,
    );
    await waitFor(() => expect(screen.getByTestId("location").textContent).toBe(parent));
    await waitFor(() => expect(screen.queryByText(heading)).not.toBeInTheDocument());
  });

  it("preserves query and fragment on a bookmarked resource route", async () => {
    const path = "/workspaces/workspace/workspace-services/service/user-resources/desktop?view=history#details";
    open(path);
    await screen.findByRole("heading", { name: "User resource desktop" });
    expect(screen.getByTestId("location").textContent).toBe(path);
  });
});

describe("navigation from an active workspace child route", () => {
  it.each([
    ["/workspaces/workspace/requests/request", "Existing request", "New request", "/workspaces/workspace/requests/new"],
    ["/workspaces/workspace/requests/new", "New airlock request", "New request", "/workspaces/workspace/requests/new"],
    ["/workspaces/workspace/users/new", "Assign users to a role", "Assign New", "/workspaces/workspace/users/new"],
  ])("keeps the parent action scoped to its workspace from %s", async (path, heading, action, expected) => {
    open(path);
    await screen.findByRole("dialog", { name: heading });
    // The modal blocks this parent control in the browser. Dispatch directly to
    // test its navigation callback with the child route still active.
    fireEvent.click(screen.getByText(action).closest("button")!);
    await waitFor(() => expect(screen.getByTestId("location").textContent).toBe(expected));
  });

  it("opens a sibling Airlock request from an active request route", async () => {
    listedRequests = [request, { ...request, id: "other", title: "Other request" }];
    open("/workspaces/workspace/requests/request");
    await screen.findByRole("dialog", { name: "Existing request" });
    // Invoke the real row callback behind the modal to check sibling resolution.
    fireEvent.doubleClick(await screen.findByText("Other request"));
    await waitFor(() =>
      expect(screen.getByTestId("location").textContent).toBe("/workspaces/workspace/requests/other"),
    );
    await screen.findByRole("dialog", { name: "Other request" });
  });

  it.each([
    ["/workspaces/workspace/requests/request", "Existing request", "New request", "/workspaces/workspace/requests/new"],
    ["/workspaces/workspace/requests/new", "New airlock request", "New request", "/workspaces/workspace/requests/new"],
    ["/workspaces/workspace/users/new", "Assign users to a role", "Assign New", "/workspaces/workspace/users/new"],
  ])("can dismiss a child and open the next panel from %s", async (path, heading, action, expected) => {
    open(path);
    await screen.findByRole("dialog", { name: heading });
    fireEvent.click(
      screen
        .getAllByRole("button", { name: "Close" })
        .find((button) => button.classList.contains("ms-Panel-closeButton"))!,
    );
    await waitFor(() => expect(screen.queryByRole("dialog", { name: heading })).not.toBeInTheDocument());
    fireEvent.click(await screen.findByRole("button", { name: action }));
    await waitFor(() => expect(screen.getByTestId("location").textContent).toBe(expected));
  });
});

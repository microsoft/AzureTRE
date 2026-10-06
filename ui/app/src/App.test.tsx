import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { MsalProvider } from "@azure/msal-react";
import { Provider } from "react-redux";
import { App } from "./App";
import { createMockMsalInstance, createMockStore } from "./test-utils";

// Mock the auth config
vi.mock("./authConfig", () => ({
  msalConfig: {
    auth: {
      clientId: "test-client-id",
      authority: "https://login.microsoftonline.com/test-tenant",
    },
    cache: {
      cacheLocation: "sessionStorage",
    },
  },
}));

// Mock MSAL instance more thoroughly to prevent network calls
vi.mock("@azure/msal-browser", async () => {
  const actual = await vi.importActual("@azure/msal-browser");
  class MockPublicClientApplication {
    constructor() {
      // Mock the constructor
    }
    initialize = vi.fn().mockResolvedValue(undefined);
    getAllAccounts = vi.fn().mockReturnValue([]);
    getActiveAccount = vi.fn().mockReturnValue(null);
    addEventCallback = vi.fn();
    removeEventCallback = vi.fn();
    getConfiguration = vi.fn().mockReturnValue({
      auth: {
        clientId: "test-client-id",
        authority: "https://login.microsoftonline.com/test-tenant",
      },
    });
  }

  return {
    ...actual,
    PublicClientApplication: MockPublicClientApplication,
  };
});

// Mock the API hook
vi.mock("./hooks/useAuthApiCall", () => ({
  useAuthApiCall: () => vi.fn().mockResolvedValue([]),
  HttpMethod: { Get: "GET" },
  ResultType: { JSON: "json" },
}));

// Mock components that might cause issues
// TopNav and WorkspaceProvider share the workspace context, so the user menu can show workspace roles.
vi.mock("./components/shared/TopNav", async () => {
  const React = await import("react");
  const { WorkspaceContext } = await import("./contexts/WorkspaceContext");
  return {
    TopNav: () => {
      const ctx = React.useContext(WorkspaceContext);
      return (
        <div data-testid="top-nav">
          Top Navigation {ctx.workspace?.properties?.display_name} {ctx.roles.join(",")}
        </div>
      );
    },
  };
});

vi.mock("./components/shared/Footer", () => ({
  Footer: () => <div data-testid="footer">Footer</div>,
}));

vi.mock("./components/root/RootLayout", () => ({
  RootLayout: () => <div data-testid="root-layout">Root Layout</div>,
}));

vi.mock("./components/workspaces/WorkspaceProvider", async () => {
  const React = await import("react");
  const { WorkspaceContext } = await import("./contexts/WorkspaceContext");
  return {
    WorkspaceProvider: () => {
      const ctx = React.useContext(WorkspaceContext);
      React.useEffect(() => {
        ctx.setWorkspace({ id: "test-workspace", properties: { display_name: "Test Workspace" } } as any);
        ctx.setRoles(["WorkspaceOwner"]);
      }, []);
      return <div data-testid="workspace-provider">Workspace Provider</div>;
    },
  };
});

vi.mock("./components/shared/create-update-resource/CreateUpdateResource", () => ({
  CreateUpdateResource: ({ isOpen }: { isOpen: boolean }) =>
    isOpen ? <div data-testid="create-update-resource">Create Update Resource</div> : null,
}));

vi.mock("./components/shared/GenericErrorBoundary", () => ({
  GenericErrorBoundary: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

const TestWrapper = ({
  children,
  initialEntries = ["/"],
}: {
  children: React.ReactNode;
  initialEntries?: string[];
}) => {
  const msalInstance = createMockMsalInstance();
  const store = createMockStore();

  return (
    <MsalProvider instance={msalInstance}>
      <Provider store={store}>
        <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
      </Provider>
    </MsalProvider>
  );
};

describe("App Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders without crashing", async () => {
    await act(async () => {
      render(
        <TestWrapper>
          <App />
        </TestWrapper>,
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId("top-nav")).toBeInTheDocument();
    });

    expect(screen.getByTestId("footer")).toBeInTheDocument();
    expect(screen.getByTestId("root-layout")).toBeInTheDocument();
  });

  it("renders logout message on logout route", async () => {
    await act(async () => {
      render(
        <TestWrapper initialEntries={["/logout"]}>
          <App />
        </TestWrapper>,
      );
    });

    await waitFor(() => {
      expect(screen.getByText("You are logged out.")).toBeInTheDocument();
    });

    expect(screen.getByText(/You are now logged out of the Azure TRE portal/)).toBeInTheDocument();
  });

  it("renders workspace provider for workspace routes", async () => {
    await act(async () => {
      render(
        <TestWrapper initialEntries={["/workspaces/test-workspace/"]}>
          <App />
        </TestWrapper>,
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId("workspace-provider")).toBeInTheDocument();
    });
  });

  it("shares the workspace context with the top navigation", async () => {
    await act(async () => {
      render(
        <TestWrapper initialEntries={["/workspaces/test-workspace/"]}>
          <App />
        </TestWrapper>,
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId("top-nav")).toHaveTextContent("Test Workspace WorkspaceOwner");
    });
  });
});

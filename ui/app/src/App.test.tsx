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
vi.mock("@azure/msal-browser", () => ({
  PublicClientApplication: vi.fn().mockImplementation(() => ({
    initialize: vi.fn().mockResolvedValue(undefined),
    getAllAccounts: vi.fn().mockReturnValue([]),
    getActiveAccount: vi.fn().mockReturnValue(null),
    addEventCallback: vi.fn(),
    removeEventCallback: vi.fn(),
    getConfiguration: vi.fn().mockReturnValue({
      auth: {
        clientId: "test-client-id",
        authority: "https://login.microsoftonline.com/test-tenant",
      },
    }),
  })),
  AuthenticationResult: vi.fn(),
  InteractionRequiredAuthError: vi.fn(),
  InteractionType: {
    Redirect: "redirect",
    Popup: "popup",
    Silent: "silent",
  },
}));

// Mock MSAL React components
vi.mock("@azure/msal-react", () => ({
  MsalProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  MsalAuthenticationTemplate: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  useMsal: vi.fn(() => ({
    instance: {
      getAllAccounts: vi.fn().mockReturnValue([]),
      getActiveAccount: vi.fn().mockReturnValue(null),
    },
    accounts: [],
  })),
  useAccount: vi.fn(() => null),
}));

// Mock the API hook
vi.mock("./hooks/useAuthApiCall", () => ({
  useAuthApiCall: () => vi.fn().mockResolvedValue([]),
  HttpMethod: { Get: "GET" },
  ResultType: { JSON: "json" },
}));

// Mock components that might cause issues
vi.mock("./components/shared/TopNav", () => ({
  TopNav: () => <div data-testid="top-nav">Top Navigation</div>,
}));

vi.mock("./components/shared/Footer", () => ({
  Footer: () => <div data-testid="footer">Footer</div>,
}));

vi.mock("./components/root/RootLayout", () => ({
  RootLayout: () => <div data-testid="root-layout">Root Layout</div>,
}));

vi.mock("./components/workspaces/WorkspaceProvider", () => ({
  WorkspaceProvider: () => <div data-testid="workspace-provider">Workspace Provider</div>,
}));

vi.mock("./components/shared/create-update-resource/CreateUpdateResource", () => ({
  CreateUpdateResource: ({ isOpen }: { isOpen: boolean }) =>
    isOpen ? <div data-testid="create-update-resource">Create Update Resource</div> : null,
}));

vi.mock("./components/shared/GenericErrorBoundary", () => ({
  GenericErrorBoundary: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

const TestWrapper = ({ children, initialEntries = ["/"] }: { children: React.ReactNode; initialEntries?: string[] }) => {
  const msalInstance = createMockMsalInstance();
  const store = createMockStore();

  return (
    <MsalProvider instance={msalInstance}>
      <Provider store={store}>
        <MemoryRouter initialEntries={initialEntries}>
          {children}
        </MemoryRouter>
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
        </TestWrapper>
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
        </TestWrapper>
      );
    });

    await waitFor(() => {
      expect(screen.getByText("You are logged out.")).toBeInTheDocument();
    });

    expect(
      screen.getByText(/You are now logged out of the Azure TRE portal/)
    ).toBeInTheDocument();
  });

  it("renders workspace provider for workspace routes", async () => {
    await act(async () => {
      render(
        <TestWrapper initialEntries={["/workspaces/test-workspace/"]}>
          <App />
        </TestWrapper>
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId("workspace-provider")).toBeInTheDocument();
    });
  });
});

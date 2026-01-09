import { vi } from 'vitest';

/**
 * Creates a mock for the useAuthApiCall hook.
 * This is used across many test files to mock API calls.
 *
 * @param mockImplementation - Optional custom implementation for the API call
 * @returns Mock function that can be used in vi.mock()
 *
 * @example
 * const mockApiCall = createMockAuthApiCall();
 * vi.mock("../../hooks/useAuthApiCall", () => ({
 *   useAuthApiCall: () => mockApiCall,
 *   HttpMethod: { Get: "GET", Post: "POST", Patch: "PATCH", Delete: "DELETE" },
 *   ResultType: { JSON: "JSON" },
 * }));
 */
export const createMockAuthApiCall = (mockImplementation?: any) => {
  return mockImplementation || vi.fn();
};

/**
 * Creates a complete mock for the useAuthApiCall hook with all HTTP methods.
 * Use this in vi.mock() calls to replace the entire hook module.
 * Returns an object that includes a reference to the mock function for testing.
 */
export const createAuthApiCallMock = (mockApiCall?: any) => {
  const apiCall = mockApiCall || vi.fn();
  const mockObject = {
    useAuthApiCall: () => apiCall,
    HttpMethod: {
      Get: "GET",
      Post: "POST",
      Patch: "PATCH",
      Delete: "DELETE",
      Put: "PUT"
    },
    ResultType: { JSON: "JSON", Text: "TEXT" },
    mockApiCall: apiCall, // Expose the mock for testing
  };

  // Attach the mock function to the module for access in tests
  (mockObject as any).__mockApiCall = apiCall;

  return mockObject;
};

/**
 * Creates a mock for the operations slice used in Redux.
 * Commonly used in components that dispatch operations.
 */
export const createOperationsSliceMock = () => ({
  addUpdateOperation: vi.fn(),
});

/**
 * Creates a mock for the ExceptionLayout component.
 * This component is frequently mocked in error handling tests.
 */
export const createExceptionLayoutMock = () => ({
  ExceptionLayout: ({ e }: any) => (
    <div data-testid="exception-layout">
      <div data-testid="exception-message">{e?.userMessage || e?.message}</div>
    </div>
  ),
});

/**
 * Creates mocks for common child components used in resource tests.
 */
export const createResourceComponentMocks = () => ({
  ResourceHeader: ({ resource, latestUpdate, readonly }: any) => (
    <div data-testid="resource-header">
      <div data-testid="resource-id">{resource?.id}</div>
      <div data-testid="resource-readonly">{readonly?.toString()}</div>
    </div>
  ),
  ResourceBody: ({ resource, readonly }: any) => (
    <div data-testid="resource-body">
      <div data-testid="resource-id">{resource?.id}</div>
      <div data-testid="resource-readonly">{readonly?.toString()}</div>
    </div>
  ),
});

/**
 * Creates a mock for API endpoints commonly used across tests.
 */
export const createApiEndpointsMock = () => ({
  ApiEndpoint: {
    Workspaces: "/api/workspaces",
    SharedServices: "/api/shared-services",
    UserResources: "/api/user-resources",
    WorkspaceServices: "/api/workspace-services",
    Templates: "/api/templates",
    Costs: "costs",
    AirlockRequests: "/api/airlock-requests",
  },
});

/**
 * Creates mocks for Redux hooks commonly used in tests.
 */
export const createReduxHookMocks = (mockDispatch?: any) => ({
  useAppDispatch: () => mockDispatch || vi.fn(),
  useAppSelector: vi.fn(),
});

/**
 * Creates mocks for React Router hooks and utilities.
 */
export const createReactRouterMocks = (mockNavigate?: any, params?: any) => ({
  useNavigate: () => mockNavigate || vi.fn(),
  useParams: () => params || {},
  useLocation: () => ({ pathname: '/test', search: '', hash: '', state: null }),
  BrowserRouter: ({ children }: any) => <div data-testid="browser-router">{children}</div>,
});

/**
 * Creates mocks for common context providers.
 */
export const createContextMocks = () => ({
  WorkspaceContext: {
    Provider: ({ children, value }: any) => (
      <div data-testid="workspace-context-provider">{children}</div>
    ),
  },
  AppRolesContext: {
    Provider: ({ children, value }: any) => (
      <div data-testid="app-roles-context-provider">{children}</div>
    ),
  },
  CostsContext: {
    Provider: ({ children, value }: any) => (
      <div data-testid="costs-context-provider">{children}</div>
    ),
  },
});

/**
 * Creates a mock for the useComponentManager hook.
 */
export const createComponentManagerMock = (mockImplementation?: any) => ({
  useComponentManager: () => mockImplementation || {
    loading: false,
    latestUpdate: null,
    componentAction: vi.fn(),
  },
});

/**
 * Creates comprehensive mocks for authentication-related modules.
 * Includes MSAL browser and react mocks.
 */
export const createAuthMocks = () => ({
  msalBrowser: {
    PublicClientApplication: vi.fn().mockImplementation(() => ({
      initialize: vi.fn().mockResolvedValue(undefined),
      getAllAccounts: vi.fn().mockReturnValue([]),
      getActiveAccount: vi.fn().mockReturnValue(null),
      acquireTokenSilent: vi.fn().mockResolvedValue({ accessToken: 'test-token' }),
      loginRedirect: vi.fn(),
      logoutRedirect: vi.fn(),
    })),
    InteractionType: { Redirect: 'redirect', Popup: 'popup' },
  },
  msalReact: {
    useMsal: () => ({
      instance: {
        getAllAccounts: vi.fn().mockReturnValue([]),
        getActiveAccount: vi.fn().mockReturnValue(null),
        acquireTokenSilent: vi.fn().mockResolvedValue({ accessToken: 'test-token' }),
      },
      accounts: [],
      inProgress: 'none',
    }),
    MsalProvider: ({ children }: any) => <div data-testid="msal-provider">{children}</div>,
    AuthenticatedTemplate: ({ children }: any) => <div data-testid="authenticated-template">{children}</div>,
    UnauthenticatedTemplate: ({ children }: any) => <div data-testid="unauthenticated-template">{children}</div>,
  },
});

/**
 * All-in-one function to create common test mocks.
 * Use this for comprehensive mocking in complex test files.
 */
export const createCommonTestMocks = () => {
  const mockApiCall = createMockAuthApiCall();
  const mockDispatch = vi.fn();
  const mockNavigate = vi.fn();

  return {
    mockApiCall,
    mockDispatch,
    mockNavigate,
    authApiCall: createAuthApiCallMock(mockApiCall),
    operationsSlice: createOperationsSliceMock(),
    exceptionLayout: createExceptionLayoutMock(),
    resourceComponents: createResourceComponentMocks(),
    apiEndpoints: createApiEndpointsMock(),
    reduxHooks: createReduxHookMocks(mockDispatch),
    reactRouter: createReactRouterMocks(mockNavigate),
    contexts: createContextMocks(),
    componentManager: createComponentManagerMock(),
    auth: createAuthMocks(),
  };
};

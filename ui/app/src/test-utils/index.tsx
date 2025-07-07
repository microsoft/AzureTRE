import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { MsalProvider } from '@azure/msal-react';
import { PublicClientApplication } from '@azure/msal-browser';
import { Provider } from 'react-redux';
import { vi } from 'vitest';
import { AppRolesContext } from '../contexts/AppRolesContext';
import { WorkspaceContext } from '../contexts/WorkspaceContext';
import { CreateUpdateResourceContext } from '../contexts/CreateUpdateResourceContext';
import { CostsContext } from '../contexts/CostsContext';
import { LoadingState } from '../models/loadingState';
import { configureStore } from '@reduxjs/toolkit';
import operationsReducer from '../components/shared/notifications/operationsSlice';

// Mock MSAL instance
export const createMockMsalInstance = () => {
  const mockMsalInstance = new PublicClientApplication({
    auth: {
      clientId: 'test-client-id',
      authority: 'https://login.microsoftonline.com/test-tenant',
    },
  });

  vi.spyOn(mockMsalInstance, 'getAllAccounts').mockReturnValue([]);
  vi.spyOn(mockMsalInstance, 'getActiveAccount').mockReturnValue(null);
  vi.spyOn(mockMsalInstance, 'initialize').mockResolvedValue();

  return mockMsalInstance;
};

// Mock Redux store
export const createMockStore = (initialState = {}) => {
  return configureStore({
    reducer: {
      operations: operationsReducer,
    },
    preloadedState: {
      operations: { items: [] },
      ...initialState,
    },
  });
};

// Default context values
export const defaultAppRolesContext = {
  roles: ['TREAdmin'],
  setAppRoles: vi.fn(),
};

export const defaultWorkspaceContext = {
  roles: ['WorkspaceOwner'],
  setRoles: vi.fn(),
  costs: [],
  setCosts: vi.fn(),
  workspace: {
    id: 'test-workspace',
    resourcePath: '/workspaces/test-workspace',
    templateName: 'base',
    templateVersion: '1.0.0',
    properties: {
      scope_id: 'test-scope',
    },
  },
  setWorkspace: vi.fn(),
  workspaceApplicationIdURI: 'test-scope',
};

export const defaultCreateUpdateResourceContext = {
  openCreateForm: vi.fn(),
};

export const defaultCostsContext = {
  loadingState: LoadingState.Ok,
  costs: [],
  setCosts: vi.fn(),
  setLoadingState: vi.fn(),
};

interface AllProvidersProps {
  children: React.ReactNode;
  msalInstance?: PublicClientApplication;
  store?: any;
  appRolesContext?: any;
  workspaceContext?: any;
  createUpdateResourceContext?: any;
  costsContext?: any;
  initialEntries?: string[];
}

const AllProviders: React.FC<AllProvidersProps> = ({
  children,
  msalInstance = createMockMsalInstance(),
  store = createMockStore(),
  appRolesContext = defaultAppRolesContext,
  workspaceContext = defaultWorkspaceContext,
  createUpdateResourceContext = defaultCreateUpdateResourceContext,
  costsContext = defaultCostsContext,
  initialEntries = ['/'],
}) => {
  return (
    <MsalProvider instance={msalInstance}>
      <Provider store={store}>
        <MemoryRouter initialEntries={initialEntries}>
          <AppRolesContext.Provider value={appRolesContext}>
            <CreateUpdateResourceContext.Provider value={createUpdateResourceContext}>
              <CostsContext.Provider value={costsContext}>
                <WorkspaceContext.Provider value={workspaceContext}>
                  {children}
                </WorkspaceContext.Provider>
              </CostsContext.Provider>
            </CreateUpdateResourceContext.Provider>
          </AppRolesContext.Provider>
        </MemoryRouter>
      </Provider>
    </MsalProvider>
  );
};

const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'> & AllProvidersProps
) => {
  const {
    msalInstance,
    store,
    appRolesContext,
    workspaceContext,
    createUpdateResourceContext,
    costsContext,
    initialEntries,
    ...renderOptions
  } = options || {};

  return render(ui, {
    wrapper: (props) => (
      <AllProviders
        {...props}
        msalInstance={msalInstance}
        store={store}
        appRolesContext={appRolesContext}
        workspaceContext={workspaceContext}
        createUpdateResourceContext={createUpdateResourceContext}
        costsContext={costsContext}
        initialEntries={initialEntries}
      />
    ),
    ...renderOptions,
  });
};

export * from '@testing-library/react';
export { customRender as render };
export * from './fluentui-mocks';
export * from './common-mocks';

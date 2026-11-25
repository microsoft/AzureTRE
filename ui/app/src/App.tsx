import React, { useCallback, useEffect, useMemo, useState } from "react";
import { DefaultPalette, IStackStyles, MessageBar, MessageBarType, Stack } from "@fluentui/react";
import "./App.scss";
import { TopNav } from "./components/shared/TopNav";
import { Routes, Route } from "react-router-dom";
import { RootLayout } from "./components/root/RootLayout";
import { WorkspaceProvider } from "./components/workspaces/WorkspaceProvider";
import { MsalAuthenticationTemplate } from "@azure/msal-react";
import { InteractionType } from "@azure/msal-browser";
import { Workspace } from "./models/workspace";
import { AppRolesContext } from "./contexts/AppRolesContext";
import { WorkspaceContext } from "./contexts/WorkspaceContext";
import { GenericErrorBoundary } from "./components/shared/GenericErrorBoundary";
import { HttpMethod, ResultType, useAuthApiCall } from "./hooks/useAuthApiCall";
import { ApiEndpoint } from "./models/apiEndpoints";
import { CreateUpdateResource } from "./components/shared/create-update-resource/CreateUpdateResource";
import { CreateUpdateResourceContext } from "./contexts/CreateUpdateResourceContext";
import { CreateFormResource, ResourceType } from "./models/resourceType";
import { Footer } from "./components/shared/Footer";
import { initializeFileTypeIcons } from "@fluentui/react-file-type-icons";
import { CostResource } from "./models/costs";
import { CostsContext } from "./contexts/CostsContext";
import { LoadingState } from "./models/loadingState";
import { isEqualJson } from "./utils/isEqualJson";

export const App: React.FunctionComponent = () => {
  const [appRoles, setAppRoles] = useState([] as Array<string>);
  const [selectedWorkspace, setSelectedWorkspace] = useState({} as Workspace);
  const [workspaceRoles, setWorkspaceRoles] = useState([] as Array<string>);
  const [workspaceCosts, setWorkspaceCosts] = useState([] as Array<CostResource>);
  const [costs, setCosts] = useState([] as Array<CostResource>);
  const [costsLoadingState, setCostsLoadingState] = useState(LoadingState.Loading);
  const [createFormOpen, setCreateFormOpen] = useState(false);
  const [createFormResource, setCreateFormResource] = useState({
    resourceType: ResourceType.Workspace,
  } as CreateFormResource);

  const apiCall = useAuthApiCall();

  // Entra omits the roles claim when the user has no app roles.
  const setAppRolesNormalized = useCallback((roles?: Array<string>) => setAppRoles(roles ?? []), []);

  // set the app roles
  useEffect(() => {
    const setAppRolesOnLoad = async () => {
      await apiCall(
        ApiEndpoint.Workspaces,
        HttpMethod.Get,
        undefined,
        undefined,
        ResultType.JSON,
        (roles?: Array<string>) => {
          setAppRolesNormalized(roles);
        },
        true,
      );
    };
    setAppRolesOnLoad();
  }, [apiCall, setAppRolesNormalized]);

  useEffect(() => initializeFileTypeIcons(), []);

  const appRolesContextValue = useMemo(
    () => ({ roles: appRoles, setAppRoles: setAppRolesNormalized }),
    [appRoles, setAppRolesNormalized],
  );

  const setWorkspaceIfChanged = useCallback(
    (w: Workspace) => setSelectedWorkspace((prev) => (isEqualJson(prev, w) ? prev : w)),
    [],
  );
  const setWorkspaceRolesIfChanged = useCallback(
    (roles: Array<string>) => setWorkspaceRoles((prev) => (isEqualJson(prev, roles) ? prev : roles)),
    [],
  );
  const setWorkspaceCostsIfChanged = useCallback(
    (c: Array<CostResource>) => setWorkspaceCosts((prev) => (isEqualJson(prev, c) ? prev : c)),
    [],
  );

  // Provided above TopNav so the user menu can show the current workspace's roles.
  const workspaceContextValue = useMemo(
    () => ({
      roles: workspaceRoles,
      setRoles: setWorkspaceRolesIfChanged,
      costs: workspaceCosts,
      setCosts: setWorkspaceCostsIfChanged,
      workspace: selectedWorkspace,
      setWorkspace: setWorkspaceIfChanged,
      workspaceApplicationIdURI: selectedWorkspace.properties?.scope_id,
    }),
    [
      workspaceRoles,
      workspaceCosts,
      selectedWorkspace,
      setWorkspaceIfChanged,
      setWorkspaceRolesIfChanged,
      setWorkspaceCostsIfChanged,
    ],
  );

  return (
    <>
      <Routes>
        <Route
          path="*"
          element={
            <MsalAuthenticationTemplate interactionType={InteractionType.Redirect}>
              <AppRolesContext.Provider value={appRolesContextValue}>
                <CreateUpdateResourceContext.Provider
                  value={{
                    openCreateForm: (createFormResource: CreateFormResource) => {
                      setCreateFormResource(createFormResource);
                      setCreateFormOpen(true);
                    },
                  }}
                >
                  <CreateUpdateResource
                    isOpen={createFormOpen}
                    onClose={() => setCreateFormOpen(false)}
                    resourceType={createFormResource.resourceType}
                    parentResource={createFormResource.resourceParent}
                    onAddResource={createFormResource.onAdd}
                    workspaceApplicationIdURI={createFormResource.workspaceApplicationIdURI}
                    updateResource={createFormResource.updateResource}
                  />
                  <WorkspaceContext.Provider value={workspaceContextValue}>
                    <Stack styles={stackStyles} className="tre-root">
                      <Stack.Item grow className="tre-top-nav">
                        <TopNav />
                      </Stack.Item>
                      <Stack.Item grow={100} className="tre-body">
                        <GenericErrorBoundary>
                          <CostsContext.Provider
                            value={{
                              loadingState: costsLoadingState,
                              costs: costs,
                              setCosts: (costs: Array<CostResource>) => {
                                setCosts(costs);
                              },
                              setLoadingState: (loadingState: LoadingState) => {
                                setCostsLoadingState(loadingState);
                              },
                            }}
                          >
                            <Routes>
                              <Route path="*" element={<RootLayout />} />
                              <Route path="/workspaces/:workspaceId//*" element={<WorkspaceProvider />} />
                            </Routes>
                          </CostsContext.Provider>
                        </GenericErrorBoundary>
                      </Stack.Item>
                      <Stack.Item grow>
                        <Footer />
                      </Stack.Item>
                    </Stack>
                  </WorkspaceContext.Provider>
                </CreateUpdateResourceContext.Provider>
              </AppRolesContext.Provider>
            </MsalAuthenticationTemplate>
          }
        />
        <Route
          path="/logout"
          element={
            <div className="tre-logout-message">
              <MessageBar messageBarType={MessageBarType.success} isMultiline={true}>
                <h2>You are logged out.</h2>
                <p>
                  You are now logged out of the Azure TRE portal. Please ensure that you also log out and close all
                  browser windows for other TRE services, such as virtual machines, that you might have open.
                </p>
              </MessageBar>
            </div>
          }
        />
      </Routes>
    </>
  );
};

const stackStyles: IStackStyles = {
  root: {
    background: DefaultPalette.white,
    height: "100vh",
  },
};

export const Admin: React.FunctionComponent = () => {
  return <h1>Admin (wip)</h1>;
};

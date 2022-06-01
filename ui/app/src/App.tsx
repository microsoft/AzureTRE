import React, { useEffect, useState } from 'react';
import { DefaultPalette, IStackStyles, MessageBar, MessageBarType, Stack } from '@fluentui/react';
import './App.scss';
import { TopNav } from './components/shared/TopNav';
import { Footer } from './components/shared/Footer';
import { Routes, Route } from 'react-router-dom';
import { RootLayout } from './components/root/RootLayout';
import { WorkspaceProvider } from './components/workspaces/WorkspaceProvider';
import { MsalAuthenticationTemplate } from '@azure/msal-react';
import { InteractionType } from '@azure/msal-browser';
import { Workspace } from './models/workspace';
import { AppRolesContext } from './contexts/AppRolesContext';
import { WorkspaceContext } from './contexts/WorkspaceContext';
import { GenericErrorBoundary } from './components/shared/GenericErrorBoundary';
import { NotificationsContext } from './contexts/NotificationsContext';
import { Operation } from './models/operation';
import { ResourceUpdate } from './models/resource';
import { HttpMethod, ResultType, useAuthApiCall } from './hooks/useAuthApiCall';
import { ApiEndpoint } from './models/apiEndpoints';

export const App: React.FunctionComponent = () => {
  const [appRoles, setAppRoles] = useState([] as Array<string>);
  const [selectedWorkspace, setSelectedWorkspace] = useState({} as Workspace);
  const [workspaceRoles, setWorkspaceRoles] = useState([] as Array<string>);
  const [operations, setOperations] = useState([] as Array<Operation>);
  const [resourceUpdates, setResourceUpdates] = useState([] as Array<ResourceUpdate>);
  const apiCall = useAuthApiCall();

  // set the app roles
  useEffect(() => {
    const setAppRolesOnLoad = async () => {
      await apiCall(ApiEndpoint.Workspaces, HttpMethod.Get, undefined, undefined, ResultType.JSON, (roles: Array<string>) => {
        setAppRoles(roles);
      }, true);
    };
   setAppRolesOnLoad();
  }, [apiCall]);

  return (
    <>
      <Routes>
        <Route path="*" element={
          <MsalAuthenticationTemplate interactionType={InteractionType.Redirect}>
            <NotificationsContext.Provider value={{
              operations: operations,
              addOperations: (ops: Array<Operation>) => {
                let stateOps = [...operations];
                ops.forEach((op: Operation) => {
                  let i = stateOps.findIndex((f: Operation) => f.id === op.id);
                  if (i > 0) {
                    stateOps.splice(i, 1, op);
                  } else {
                    stateOps.push(op);
                  }
                });
                setOperations(stateOps);
              },
              resourceUpdates: resourceUpdates,
              addResourceUpdate: (r: ResourceUpdate) => {
                let updates = [...resourceUpdates];
                let i = updates.findIndex((f: ResourceUpdate) => f.resourceId === r.resourceId);
                if (i > 0) {
                  updates.splice(i, 1, r);
                } else {
                  updates.push(r);
                }
                setResourceUpdates(updates);
              },
              clearUpdatesForResource: (resourceId: string) => { let updates = [...resourceUpdates].filter((r: ResourceUpdate) => r.resourceId !== resourceId); setResourceUpdates(updates); }
            }}>
              <AppRolesContext.Provider value={{
                roles: appRoles,
                setAppRoles: (roles: Array<string>) => { setAppRoles(roles) }
              }}>
                <Stack styles={stackStyles} className='tre-root'>
                  <Stack.Item grow className='tre-top-nav'>
                    <TopNav />
                  </Stack.Item>
                  <Stack.Item grow={100} className='tre-body'>
                    <GenericErrorBoundary>
                      <Routes>
                        <Route path="*" element={<RootLayout />} />
                        <Route path="/workspaces/:workspaceId//*" element={
                          <WorkspaceContext.Provider value={{
                            roles: workspaceRoles,
                            setRoles: (roles: Array<string>) => { console.warn("Workspace roles", roles); setWorkspaceRoles(roles) },
                            workspace: selectedWorkspace,
                            setWorkspace: (w: Workspace) => { console.warn("Workspace set", w); setSelectedWorkspace(w) },
                            workspaceClientId: selectedWorkspace.properties?.scope_id.replace("api://", "")
                          }}>
                            <WorkspaceProvider />
                          </WorkspaceContext.Provider>
                        } />
                      </Routes>
                    </GenericErrorBoundary>
                  </Stack.Item>
                  <Stack.Item grow>
                    <Footer />
                  </Stack.Item>
                </Stack>
              </AppRolesContext.Provider>
            </NotificationsContext.Provider>
          </MsalAuthenticationTemplate>
        } />
        <Route path='/logout' element={
          <div className='tre-logout-message'>
            <MessageBar
              messageBarType={MessageBarType.success}
              isMultiline={true}
            >
              <h2>You are logged out.</h2>
              <p>It's a good idea to close your browser windows.</p>
            </MessageBar>
          </div>} />
      </Routes>
    </>
  );
};

const stackStyles: IStackStyles = {
  root: {
    background: DefaultPalette.white,
    height: '100vh',
  },
};

export const Admin: React.FunctionComponent = () => {
  return (
    <h1>Admin (wip)</h1>
  )
}






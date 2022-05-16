import React, { useState } from 'react';
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
import { RootRolesContext } from './components/shared/RootRolesContext';
import { WorkspaceRolesContext } from './components/workspaces/WorkspaceRolesContext';
import { GenericErrorBoundary } from './components/shared/GenericErrorBoundary';
import { NotificationsContext } from './components/shared/notifications/NotificationsContext';
import { Operation } from './models/operation';

export const App: React.FunctionComponent = () => {
  const [selectedWorkspace, setSelectedWorkspace] = useState({} as Workspace);
  const [latestOperation, setLatestOperation] = useState({} as Operation);

  return (
    <>
      <Routes>
        <Route path="*" element={
          <MsalAuthenticationTemplate interactionType={InteractionType.Redirect}>
            <NotificationsContext.Provider value={{ latestOperation: latestOperation, addOperation: (op: Operation) => {setLatestOperation(op);}}}>
              <RootRolesContext.Provider value={{ roles: [] as Array<string> }}>
                <Stack styles={stackStyles} className='tre-root'>
                  <Stack.Item grow className='tre-top-nav'>
                    <TopNav />
                  </Stack.Item>
                  <Stack.Item grow={100} className='tre-body'>
                    <GenericErrorBoundary>
                      <Routes>
                        <Route path="*" element={<RootLayout selectWorkspace={(ws: Workspace) => setSelectedWorkspace(ws)} />} />
                        <Route path="/workspaces/:workspaceId//*" element={
                          <WorkspaceRolesContext.Provider value={{ roles: [] as Array<string> }}>
                            <WorkspaceProvider workspace={selectedWorkspace} />
                          </WorkspaceRolesContext.Provider>
                        } />
                      </Routes>
                    </GenericErrorBoundary>
                  </Stack.Item>
                  <Stack.Item grow>
                    <Footer />
                  </Stack.Item>
                </Stack>
              </RootRolesContext.Provider>
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






import React, { useState } from 'react';
import { DefaultPalette, IStackStyles, Stack } from '@fluentui/react';
import './App.scss';
import { TopNav } from './components/shared/TopNav';
import { Footer } from './components/shared/Footer';
import { Routes, Route } from 'react-router-dom';
import { HomeLayout } from './components/root/HomeLayout';
import { WorkspaceProvider } from './components/workspaces/WorkspaceProvider';
import { AuthenticatedTemplate, useMsalAuthentication } from '@azure/msal-react';
import { InteractionType } from '@azure/msal-browser';
import { Workspace } from './models/workspace';
import { RootRolesContext } from './components/shared/RootRolesContext';
import { WorkspaceRolesContext } from './components/workspaces/WorkspaceRolesContext';

// TODO:
// - handle auth token timeouts that require user intervention
// - log out

export const App: React.FunctionComponent = () => {
  useMsalAuthentication(InteractionType.Redirect);
  const [selectedWorkspace, setSelectedWorkspace] = useState({} as Workspace);

  return (
    <AuthenticatedTemplate>
      <RootRolesContext.Provider value={{ roles: [] as Array<String> }}>
        <Stack styles={stackStyles} className='tre-root'>
          <Stack.Item grow className='tre-top-nav'>
            <TopNav />
          </Stack.Item>
          <Stack.Item grow={100} className='tre-body'>
            <Routes>
              <Route path="*" element={<HomeLayout selectWorkspace={(ws: Workspace) => setSelectedWorkspace(ws)} />} />
              <Route path="/workspaces/:workspaceId//*" element={
                <WorkspaceRolesContext.Provider value={{ roles: [] as Array<String> }}>
                  <WorkspaceProvider workspace={selectedWorkspace} />
                </WorkspaceRolesContext.Provider>
              } />
            </Routes>
          </Stack.Item>
          <Stack.Item grow>
            <Footer />
          </Stack.Item>
        </Stack>
      </RootRolesContext.Provider>
    </AuthenticatedTemplate>
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






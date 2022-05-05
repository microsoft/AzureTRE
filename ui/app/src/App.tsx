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


export const App: React.FunctionComponent = () => {
  useMsalAuthentication(InteractionType.Redirect);
  const [selectedWorkspace, setSelectedWorkspace] = useState({} as Workspace);

  return (
    <AuthenticatedTemplate>
      <Stack styles={stackStyles} className='tre-root'>
        <Stack.Item grow>
          <TopNav />
        </Stack.Item>

        <Stack.Item grow={100} className='tre-body'>
          <Stack horizontal className='tre-body-inner'>

            <Routes>
              <Route path="*" element={<HomeLayout selectWorkspace={(ws: Workspace) => setSelectedWorkspace(ws)} />} />
              <Route path="/workspaces/:workspaceId//*" element={<WorkspaceProvider workspace={selectedWorkspace}/>} />
            </Routes>

          </Stack>
        </Stack.Item>
        <Stack.Item grow>
          <Footer />
        </Stack.Item>
      </Stack>
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






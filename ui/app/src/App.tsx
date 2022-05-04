import React from 'react';
import { DefaultPalette, IStackStyles, Stack } from '@fluentui/react';
import './App.scss';
import { TopNav } from './components/shared/TopNav';
import { Footer } from './components/shared/Footer';
import { Routes, Route } from 'react-router-dom';
import { HomeLayout } from './components/root/HomeLayout';
import { WorkspaceLayout } from './components/workspaces/WorkspaceLayout';


export const App: React.FunctionComponent = () => {
  return (
    <Stack styles={stackStyles} className='tre-root'>
      <Stack.Item grow>
        <TopNav />
      </Stack.Item>
     
      <Stack.Item grow={100} className='tre-body'>
        <Stack horizontal className='tre-body-inner'>
          
         <Routes>
           <Route path="*" element={<HomeLayout />} />
           <Route path="/workspaces/:workspaceId//*" element={<WorkspaceLayout />} />
         </Routes>

        </Stack>
      </Stack.Item>
     
      <Stack.Item grow>
        <Footer />
      </Stack.Item>
    </Stack>
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






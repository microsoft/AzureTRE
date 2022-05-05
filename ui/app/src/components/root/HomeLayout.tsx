import { Stack } from '@fluentui/react';
import React from 'react';
import { Route, Routes } from 'react-router-dom';
import { Admin } from '../../App';
import { Workspace } from '../../models/workspace';
import { HomeDashboard } from './HomeDashboard';
import { LeftNav } from './LeftNav';

interface HomeLayoutProps {
  selectWorkspace: (workspace: Workspace) => void
}

export const HomeLayout: React.FunctionComponent<HomeLayoutProps> = (props:HomeLayoutProps) => {
  return (
    <>
      <Stack.Item className='tre-left-nav'>
        <LeftNav />
      </Stack.Item><Stack.Item className='tre-body-content'>
        <Routes>
          <Route path="/" element={<HomeDashboard selectWorkspace={props.selectWorkspace}/>} />
          <Route path="/admin" element={<Admin />} />
        </Routes>
      </Stack.Item>
    </>
  );
};

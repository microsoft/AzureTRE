import { Stack } from '@fluentui/react';
import React from 'react';
import { Route, Routes } from 'react-router-dom';
import { UserResourceItem } from './UserResourceItem';
import { WorkspaceBreadcrumb } from './WorkspaceBreadcrumb';
import { WorkspaceItem } from './WorkspaceItem';
import { WorkspaceLeftNav } from './WorkspaceLeftNav';
import { WorkspaceServiceItem } from './WorkspaceServiceItem';

export const WorkspaceLayout: React.FunctionComponent = () => {
  return (
    <>
      <Stack.Item className='tre-left-nav'>
        <WorkspaceLeftNav />
      </Stack.Item>
      <Stack.Item className='tre-body-content'>
      <Stack>
        <Stack.Item grow>
          <WorkspaceBreadcrumb />
        </Stack.Item>
        <Stack.Item grow={100}>
        <Routes>
          <Route path="/" element={<WorkspaceItem />} />
          <Route path="workspace-services/:workspaceServiceId/*" element={<WorkspaceServiceItem />} />
          <Route path="workspace-services/:workspaceServiceId/user-resources/:userResourceId/*" element={<UserResourceItem />} />
        </Routes>
        </Stack.Item>
      </Stack>
       
        
      </Stack.Item>
    </>
  );
};

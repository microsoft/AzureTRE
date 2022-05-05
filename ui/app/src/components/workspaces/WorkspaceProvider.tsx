import { Stack } from '@fluentui/react';
import React, { useEffect, useState } from 'react';
import { Route, Routes, useParams } from 'react-router-dom';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { Workspace } from '../../models/workspace';
import { WorkspaceService } from '../../models/workspaceService';
import { HttpMethod, useAuthApiCall } from '../../useAuthApiCall';
import { UserResourceItem } from './UserResourceItem';
import { WorkspaceBreadcrumb } from './WorkspaceBreadcrumb';
import { WorkspaceItem } from './WorkspaceItem';
import { WorkspaceLeftNav } from './WorkspaceLeftNav';
import { WorkspaceServiceItem } from './WorkspaceServiceItem';

interface WorkspaceProviderProps {
  workspace?: Workspace
}

export const WorkspaceProvider: React.FunctionComponent<WorkspaceProviderProps> = (props:WorkspaceProviderProps) => {
  const apiCall = useAuthApiCall();
  const [workspace, setWorkspace] = useState({} as Workspace);
  const [selectedWorkspaceService, setSelectedWorkspaceService] = useState({} as WorkspaceService);
  const { workspaceId } = useParams();

  useEffect(() => {
    const getWorkspace = async () => {
      // have we been passed the workspace? use it if we have - else (it's a fresh load at this route) - load it before rendering the sub components
      if (props.workspace && props.workspace.id) {
        setWorkspace(props.workspace);
      } else {
        const w = await apiCall(`${ApiEndpoint.Workspaces}/${workspaceId}`, HttpMethod.Get);
        setWorkspace(w.workspace);
      }
      
    };
    getWorkspace();
  }, [apiCall, props.workspace, workspaceId]);

  return (
    <>
    {
      workspace.id && (
          <>
          <Stack.Item className='tre-left-nav'>
            <WorkspaceLeftNav workspace={workspace} setWorkspaceService={(ws: WorkspaceService) => setSelectedWorkspaceService(ws)} />
          </Stack.Item><Stack.Item className='tre-body-content'>
              <Stack>
                <Stack.Item grow>
                  <WorkspaceBreadcrumb />
                </Stack.Item>
                <Stack.Item grow={100}>
                    <Routes>
                      <Route path="/" element={<WorkspaceItem workspace={workspace} />} />
                      <Route path="workspace-services/:workspaceServiceId/*" element={<WorkspaceServiceItem workspace={workspace} workspaceService={selectedWorkspaceService} />} />
                      <Route path="workspace-services/:workspaceServiceId/user-resources/:userResourceId/*" element={<UserResourceItem workspace={workspace} />} />
                    </Routes>
                </Stack.Item>
              </Stack>
            </Stack.Item>
            </>
      )
    }
    </>
  );
};

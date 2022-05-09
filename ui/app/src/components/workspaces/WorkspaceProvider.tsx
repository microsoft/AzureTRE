import { Stack } from '@fluentui/react';
import React, { useContext, useEffect, useState } from 'react';
import { Route, Routes, useParams } from 'react-router-dom';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { UserResource } from '../../models/userResource';
import { Workspace } from '../../models/workspace';
import { WorkspaceService } from '../../models/workspaceService';
import { HttpMethod, ResultType, useAuthApiCall } from '../../useAuthApiCall';
import { UserResourceItem } from './UserResourceItem';
import { WorkspaceBreadcrumb } from './WorkspaceBreadcrumb';
import { WorkspaceHeader } from './WorkspaceHeader';
import { WorkspaceItem } from './WorkspaceItem';
import { WorkspaceLeftNav } from './WorkspaceLeftNav';
import { WorkspaceServiceItem } from './WorkspaceServiceItem';
import config from '../../config.json';
import { WorkspaceRolesContext } from './WorkspaceRolesContext';

interface WorkspaceProviderProps {
  workspace?: Workspace
}

export const WorkspaceProvider: React.FunctionComponent<WorkspaceProviderProps> = (props: WorkspaceProviderProps) => {
  const apiCall = useAuthApiCall();
  const [workspace, setWorkspace] = useState({} as Workspace);
  const [selectedWorkspaceService, setSelectedWorkspaceService] = useState({} as WorkspaceService);
  const [selectedUserResource, setSelectedUserResource] = useState({} as UserResource);
  const workspaceRoles = useContext(WorkspaceRolesContext);
  const { workspaceId } = useParams();


  useEffect(() => {
    const getWorkspace = async () => {
      // have we been passed the workspace? use it if we have - else (it's a fresh load at this route) - load it before rendering the sub components
      let ws = props.workspace && props.workspace.id ?
        props.workspace :
        (await apiCall(`${ApiEndpoint.Workspaces}/${workspaceId}`, HttpMethod.Get)).workspace;

      // now 'authenticate' against the workspace - just get the roles for this workspace (tokenOnly = true)
      await apiCall(`${ApiEndpoint.Workspaces}/${workspaceId}`, HttpMethod.Get, ws.properties.app_id, undefined, ResultType.None, (roles: Array<String>) => {
        config.debug && console.log(`Workspace roles for ${ws.properties?.display_name}`, roles);
        workspaceRoles.roles = roles;
      }, true);

      // set the workspace roles context, which can be used by all subcomponents in the tree
      setWorkspace(ws);
    };
    getWorkspace();
  }, [apiCall, props.workspace, workspaceId, workspaceRoles]);

  return (
    <>
      {
        workspace.id && (
          <>
          <WorkspaceHeader workspace={workspace} />
            <Stack horizontal className='tre-body-inner'>
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
                      <Route path="workspace-services/:workspaceServiceId/*" element={<WorkspaceServiceItem workspace={workspace} workspaceService={selectedWorkspaceService} setUserResource={(userResource:UserResource) => setSelectedUserResource(userResource)} />} />
                      <Route path="workspace-services/:workspaceServiceId/user-resources/:userResourceId/*" element={<UserResourceItem workspace={workspace} userResource={selectedUserResource} />} />
                    </Routes>
                  </Stack.Item>
                </Stack>
              </Stack.Item>
            </Stack>
          </>
        )
      }
    </>
  );
};

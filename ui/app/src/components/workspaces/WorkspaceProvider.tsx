import { MessageBar, MessageBarType, Spinner, SpinnerSize, Stack } from '@fluentui/react';
import React, { useContext, useEffect, useRef, useState } from 'react';
import { Route, Routes, useParams } from 'react-router-dom';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { UserResource } from '../../models/userResource';
import { Workspace } from '../../models/workspace';
import { WorkspaceService } from '../../models/workspaceService';
import { HttpMethod, ResultType, useAuthApiCall } from '../../useAuthApiCall';
import { UserResourceItem } from './UserResourceItem';
import { WorkspaceHeader } from './WorkspaceHeader';
import { WorkspaceItem } from './WorkspaceItem';
import { WorkspaceLeftNav } from './WorkspaceLeftNav';
import { WorkspaceServiceItem } from './WorkspaceServiceItem';
import config from '../../config.json';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import { WorkspaceServices } from './WorkspaceServices';

interface WorkspaceProviderProps {
  workspace?: Workspace
}

export const WorkspaceProvider: React.FunctionComponent<WorkspaceProviderProps> = (props: WorkspaceProviderProps) => {
  const apiCall = useAuthApiCall();
  const [workspace, setWorkspace] = useState({} as Workspace);
  const [selectedWorkspaceService, setSelectedWorkspaceService] = useState({} as WorkspaceService);
  const [selectedUserResource, setSelectedUserResource] = useState({} as UserResource);
  const [workspaceServices, setWorkspaceServices] = useState([] as Array<WorkspaceService>)
  const workspaceCtx = useRef(useContext(WorkspaceContext));
  const [loadingState, setLoadingState] = useState('loading');
  const { workspaceId } = useParams();

  useEffect(() => {
    const getWorkspace = async () => {
      // have we been passed the workspace? use it if we have - else (it's a fresh load at this route) - load it before rendering the sub components
      try {
        let ws = props.workspace && props.workspace.id ?
          props.workspace :
          (await apiCall(`${ApiEndpoint.Workspaces}/${workspaceId}`, HttpMethod.Get)).workspace;

        // set the workspace, which is passed to all child components
        setWorkspace(ws);

        // now 'authenticate' against the workspace - just get the roles for this workspace (tokenOnly = true)
        await apiCall(`${ApiEndpoint.Workspaces}/${workspaceId}`, HttpMethod.Get, ws.properties.app_id, undefined, ResultType.None, (roles: Array<string>) => {
          config.debug && console.log(`Workspace roles for ${ws.properties?.display_name}`, roles);
          workspaceCtx.current.setRoles(roles);
          setLoadingState(roles && roles.length > 0 ? 'ok' : 'denied');
        }, true);

        // get workspace services to pass to nav + ws services page
        const workspaceServices = await apiCall(`${ApiEndpoint.Workspaces}/${ws.id}/${ApiEndpoint.WorkspaceServices}`, HttpMethod.Get, ws.properties.app_id);
        setWorkspaceServices(workspaceServices.workspaceServices);

      } catch {
        setLoadingState('error');
      }
    };
    getWorkspace();
  }, [apiCall, props.workspace, workspaceId]);

  switch (loadingState) {
    case 'ok':
      return (
        <>
          <WorkspaceHeader workspace={workspace} />
          <Stack horizontal className='tre-body-inner'>
            <Stack.Item className='tre-left-nav'>
              <WorkspaceLeftNav workspace={workspace} workspaceServices={workspaceServices} setWorkspaceService={(ws: WorkspaceService) => setSelectedWorkspaceService(ws)} />
            </Stack.Item><Stack.Item className='tre-body-content'>
              <Stack>
                <Stack.Item grow={100}>
                  <Routes>
                    <Route path="/" element={<WorkspaceItem workspace={workspace} />} />
                    <Route path="workspace-services" element={<WorkspaceServices workspace={workspace} workspaceServices={workspaceServices} setWorkspaceService={(ws: WorkspaceService) => setSelectedWorkspaceService(ws)}/>} />
                    <Route path="workspace-services/:workspaceServiceId/*" element={<WorkspaceServiceItem workspace={workspace} workspaceService={selectedWorkspaceService} setUserResource={(userResource: UserResource) => setSelectedUserResource(userResource)} />} />
                    <Route path="workspace-services/:workspaceServiceId/user-resources/:userResourceId/*" element={<UserResourceItem workspace={workspace} userResource={selectedUserResource} />} />
                  </Routes>
                </Stack.Item>
              </Stack>
            </Stack.Item>
          </Stack>
        </>
      );
    case 'denied':
      return (
        <MessageBar
          messageBarType={MessageBarType.warning}
          isMultiline={true}
        >
          <h3>Access Denied</h3>
          <p>
            You do not have access to this Workspace. If you feel you should have access, please speak to your TRE Administrator. <br />
            If you have recently been given access, you may need to clear you browser local storage and refresh.</p>
        </MessageBar>
      );
    case 'error':
      return (
        <MessageBar
          messageBarType={MessageBarType.error}
          isMultiline={true}
        >
          <h3>Error retrieving workspace</h3>
          <p>There was an error retrieving this workspace. Please see the browser console for details.</p>
        </MessageBar>
      )
    default:
      return (
        <div style={{ marginTop: '20px' }}>
          <Spinner label="Loading Workspace" ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
        </div>
      )
  }
};

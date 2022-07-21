import { MessageBar, MessageBarType, Spinner, SpinnerSize, Stack } from '@fluentui/react';
import React, { useContext, useEffect, useRef, useState } from 'react';
import { Route, Routes, useParams } from 'react-router-dom';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { WorkspaceService } from '../../models/workspaceService';
import { HttpMethod, ResultType, useAuthApiCall } from '../../hooks/useAuthApiCall';
import { WorkspaceHeader } from './WorkspaceHeader';
import { WorkspaceItem } from './WorkspaceItem';
import { WorkspaceLeftNav } from './WorkspaceLeftNav';
import { WorkspaceServiceItem } from './WorkspaceServiceItem';
import config from '../../config.json';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import { WorkspaceServices } from './WorkspaceServices';
import { Workspace } from '../../models/workspace';
import { SharedService } from '../../models/sharedService';
import { SharedServices } from '../shared/SharedServices';
import { SharedServiceItem } from '../shared/SharedServiceItem';

export const WorkspaceProvider: React.FunctionComponent = () => {
  const apiCall = useAuthApiCall();
  const [selectedWorkspaceService, setSelectedWorkspaceService] = useState({} as WorkspaceService);
  const [workspaceServices, setWorkspaceServices] = useState([] as Array<WorkspaceService>)
  const [sharedServices, setSharedServices] = useState([] as Array<SharedService>)
  const workspaceCtx = useRef(useContext(WorkspaceContext));
  const [loadingState, setLoadingState] = useState('loading');
  const { workspaceId } = useParams();

  // set workspace context from url
  useEffect(() => {
    const getWorkspace = async () => {
      try {
        // get the workspace
        const ws = (await apiCall(`${ApiEndpoint.Workspaces}/${workspaceId}`, HttpMethod.Get)).workspace;
        workspaceCtx.current.setWorkspace(ws);
        const ws_application_id_uri = ws.properties.scope_id;

        // use the client ID to get a token against the workspace (tokenOnly), and set the workspace roles in the context
        let wsRoles: Array<string> = [];
        await apiCall(`${ApiEndpoint.Workspaces}/${workspaceId}`, HttpMethod.Get, ws_application_id_uri, undefined, ResultType.JSON, (roles: Array<string>) => {
          config.debug && console.log(`Workspace roles for ${workspaceId}`, roles);
          workspaceCtx.current.setRoles(roles);
          wsRoles = roles;
        }, true);

        // get workspace services to pass to nav + ws services page
        const workspaceServices = await apiCall(`${ApiEndpoint.Workspaces}/${ws.id}/${ApiEndpoint.WorkspaceServices}`, HttpMethod.Get, ws_application_id_uri);
        setWorkspaceServices(workspaceServices.workspaceServices);
        setLoadingState(wsRoles && wsRoles.length > 0 ? 'ok' : 'denied');

        // get shared services to pass to nav shared services pages
        const sharedServices = await apiCall(ApiEndpoint.SharedServices, HttpMethod.Get);
        setSharedServices(sharedServices.sharedServices);

      } catch {
        setLoadingState('error');
      }
    };
    getWorkspace();

    let ctx = workspaceCtx.current;

    // run this on onmount - to clear the context
    return (() => {
      ctx.setRoles([]);
      ctx.setWorkspace({} as Workspace);
    });
  }, [apiCall, workspaceId]);

  const addWorkspaceService = (w: WorkspaceService) => {
    let ws = [...workspaceServices]
    ws.push(w);
    setWorkspaceServices(ws);
  }

  const updateWorkspaceService = (w: WorkspaceService) => {
    let i = workspaceServices.findIndex((f: WorkspaceService) => f.id === w.id);
    let ws = [...workspaceServices]
    ws.splice(i, 1, w);
    setWorkspaceServices(ws);
  }

  const removeWorkspaceService = (w: WorkspaceService) => {
    let i = workspaceServices.findIndex((f: WorkspaceService) => f.id === w.id);
    let ws = [...workspaceServices];
    console.log("removing WS...", ws[i]);
    ws.splice(i, 1);
    setWorkspaceServices(ws);
  }

  switch (loadingState) {
    case 'ok':
      return (
        <>
          <WorkspaceHeader />
          <Stack horizontal className='tre-body-inner'>
            <Stack.Item className='tre-left-nav'>
              <WorkspaceLeftNav
                workspaceServices={workspaceServices}
                sharedServices={sharedServices}
                setWorkspaceService={(ws: WorkspaceService) => setSelectedWorkspaceService(ws)}
                addWorkspaceService={(ws: WorkspaceService) => addWorkspaceService(ws)} />
            </Stack.Item><Stack.Item className='tre-body-content'>
              <Stack>
                <Stack.Item grow={100}>
                  <Routes>
                    <Route path="/" element={<>
                      <WorkspaceItem />
                      <WorkspaceServices workspaceServices={workspaceServices}
                        setWorkspaceService={(ws: WorkspaceService) => setSelectedWorkspaceService(ws)}
                        addWorkspaceService={(ws: WorkspaceService) => addWorkspaceService(ws)}
                        updateWorkspaceService={(ws: WorkspaceService) => updateWorkspaceService(ws)}
                        removeWorkspaceService={(ws: WorkspaceService) => removeWorkspaceService(ws)} />
                    </>} />
                    <Route path="workspace-services" element={
                      <WorkspaceServices workspaceServices={workspaceServices}
                        setWorkspaceService={(ws: WorkspaceService) => setSelectedWorkspaceService(ws)}
                        addWorkspaceService={(ws: WorkspaceService) => addWorkspaceService(ws)}
                        updateWorkspaceService={(ws: WorkspaceService) => updateWorkspaceService(ws)}
                        removeWorkspaceService={(ws: WorkspaceService) => removeWorkspaceService(ws)}
                      />
                    } />
                    <Route path="workspace-services/:workspaceServiceId/*" element={
                      <WorkspaceServiceItem
                        workspaceService={selectedWorkspaceService}
                        updateWorkspaceService={(ws: WorkspaceService) => updateWorkspaceService(ws)}
                        removeWorkspaceService={(ws: WorkspaceService) => removeWorkspaceService(ws)} />
                    } />
                    <Route path="shared-services" element={
                      <SharedServices readonly={true} />
                    } />
                    <Route path="shared-services/:sharedServiceId/*" element={
                      <SharedServiceItem readonly={true} />
                    } />
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

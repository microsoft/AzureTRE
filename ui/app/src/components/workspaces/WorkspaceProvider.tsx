import { FontIcon, Spinner, SpinnerSize, Stack, getTheme, mergeStyles } from '@fluentui/react';
import React, { useContext, useEffect, useRef, useState } from 'react';
import { Route, Routes, useParams } from 'react-router-dom';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { WorkspaceService } from '../../models/workspaceService';
import { HttpMethod, ResultType, useAuthApiCall } from '../../hooks/useAuthApiCall';
import { WorkspaceHeader } from './WorkspaceHeader';
import { WorkspaceItem } from './WorkspaceItem';
import { WorkspaceLeftNav } from './WorkspaceLeftNav';
import { WorkspaceServiceItem } from './WorkspaceServiceItem';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import { WorkspaceServices } from './WorkspaceServices';
import { Workspace } from '../../models/workspace';
import { SharedService } from '../../models/sharedService';
import { SharedServices } from '../shared/SharedServices';
import { SharedServiceItem } from '../shared/SharedServiceItem';
import { Airlock } from '../shared/airlock/Airlock';
import { APIError } from '../../models/exceptions';
import { LoadingState } from '../../models/loadingState';
import { ExceptionLayout } from '../shared/ExceptionLayout';
import { AppRolesContext } from '../../contexts/AppRolesContext';
import { RoleName, WorkspaceRoleName } from '../../models/roleNames';

export const WorkspaceProvider: React.FunctionComponent = () => {
  const apiCall = useAuthApiCall();
  const [selectedWorkspaceService, setSelectedWorkspaceService] = useState({} as WorkspaceService);
  const [workspaceServices, setWorkspaceServices] = useState([] as Array<WorkspaceService>);
  const [sharedServices, setSharedServices] = useState([] as Array<SharedService>);
  const workspaceCtx = useRef(useContext(WorkspaceContext));
  const [wsRoles, setWSRoles] = useState([] as Array<string>);
  const [loadingState, setLoadingState] = useState(LoadingState.Loading);
  const [apiError, setApiError] = useState({} as APIError);
  const { workspaceId } = useParams();
  const [costApiError, setCostApiError] = useState({} as APIError);

  const appRoles = useContext(AppRolesContext);
  const [isTREAdminUser, setIsTREAdminUser] = useState(false);

  // set workspace context from url
  useEffect(() => {

    const getWorkspace = async () => {
      try {
        // get the workspace - first we get the scope_id so we can auth against the right aad app
        let scopeId = (await apiCall(`${ApiEndpoint.Workspaces}/${workspaceId}/scopeid`, HttpMethod.Get)).workspaceAuth.scopeId;

        const authProvisioned = scopeId !== "";

        let wsRoles: Array<string> = [];
        let ws: Workspace = {} as Workspace;

        if (authProvisioned) {
          // use the client ID to get a token against the workspace (tokenOnly), and set the workspace roles in the context
          await apiCall(`${ApiEndpoint.Workspaces}/${workspaceId}`, HttpMethod.Get, scopeId,
            undefined, ResultType.JSON, (roles: Array<string>) => {
              wsRoles = roles;
            }, true);
        }

        if (wsRoles && wsRoles.length > 0) {
          ws = (await apiCall(`${ApiEndpoint.Workspaces}/${workspaceId}`, HttpMethod.Get, scopeId)).workspace;
          workspaceCtx.current.setWorkspace(ws);
          workspaceCtx.current.setRoles(wsRoles);
          setWSRoles(wsRoles);

          // get workspace services to pass to nav + ws services page
          const workspaceServices = await apiCall(`${ApiEndpoint.Workspaces}/${ws.id}/${ApiEndpoint.WorkspaceServices}`,
            HttpMethod.Get, ws.properties.scope_id);
          setWorkspaceServices(workspaceServices.workspaceServices);
          // get shared services to pass to nav shared services pages
          const sharedServices = await apiCall(ApiEndpoint.SharedServices, HttpMethod.Get);
          setSharedServices(sharedServices.sharedServices);
          setLoadingState(LoadingState.Ok);
        } else if (appRoles.roles.includes(RoleName.TREAdmin)) {
          ws = (await apiCall(`${ApiEndpoint.Workspaces}/${workspaceId}`, HttpMethod.Get)).workspace;
          workspaceCtx.current.setWorkspace(ws);
          setLoadingState(LoadingState.Ok);
          setIsTREAdminUser(true);
        } else {
          let e = new APIError();
          e.status = 403;
          e.userMessage = "User does not have a role assigned in the workspace or the TRE Admin role assigned";
          e.endpoint = `${ApiEndpoint.Workspaces}/${workspaceId}`;
          throw e;
        }

      } catch (e: any) {
        if (e.status === 401 || e.status === 403) {
          setApiError(e);
          setLoadingState(LoadingState.AccessDenied);
        } else {
          e.userMessage = 'Error retrieving workspace';
          setApiError(e);
          setLoadingState(LoadingState.Error);
        }
      }
    };
    getWorkspace();

    let ctx = workspaceCtx.current;

    // Return a function to clear the context on unmount
    return () => {
      ctx.setRoles([]);
      ctx.setWorkspace({} as Workspace);
    };
  }, [apiCall, workspaceId, isTREAdminUser, appRoles.roles]);

  useEffect(() => {
    const getWorkspaceCosts = async () => {
      try {
        // TODO: amend when costs enabled in API for WorkspaceRoleName.Researcher
        if(wsRoles.includes(WorkspaceRoleName.WorkspaceOwner)){
          let scopeId = (await apiCall(`${ApiEndpoint.Workspaces}/${workspaceId}/scopeid`, HttpMethod.Get)).workspaceAuth.scopeId;
          const r = await apiCall(`${ApiEndpoint.Workspaces}/${workspaceId}/${ApiEndpoint.Costs}`, HttpMethod.Get, scopeId, undefined, ResultType.JSON);
          const costs = [
            ...r.costs,
            ...r.workspace_services,
            ...r.workspace_services.flatMap((ws: { user_resources: any; }) => [
              ...ws.user_resources
            ])
          ];
          workspaceCtx.current.setCosts(costs);
        }
      }
      catch (e: any) {
        if (e instanceof APIError) {
          if (e.status === 404 /*subscription not supported*/) {
          }
          else if (e.status === 429 /*too many requests*/ || e.status === 503 /*service unavaiable*/) {
            let msg = JSON.parse(e.message);
            let retryAfter = Number(msg.error["retry-after"]);
            setTimeout(getWorkspaceCosts, retryAfter * 1000);
          }
          else {
            e.userMessage = 'Error retrieving costs';
          }
        }
        else {
          e.userMessage = 'Error retrieving costs';
        }
        setCostApiError(e);
      }
    };

    getWorkspaceCosts();
  },[apiCall, workspaceId, wsRoles]);

  const addWorkspaceService = (w: WorkspaceService) => {
    let ws = [...workspaceServices];
    ws.push(w);
    setWorkspaceServices(ws);
  };

  const updateWorkspaceService = (w: WorkspaceService) => {
    let i = workspaceServices.findIndex((f: WorkspaceService) => f.id === w.id);
    let ws = [...workspaceServices];
    ws.splice(i, 1, w);
    setWorkspaceServices(ws);
  };

  const removeWorkspaceService = (w: WorkspaceService) => {
    let i = workspaceServices.findIndex((f: WorkspaceService) => f.id === w.id);
    let ws = [...workspaceServices];
    ws.splice(i, 1);
    setWorkspaceServices(ws);
  };

  switch (loadingState) {
    case LoadingState.Ok:
      return (
        <>
          {
            costApiError.message &&
            <ExceptionLayout e={costApiError} />
          }
          <WorkspaceHeader />
          <Stack horizontal className='tre-body-inner'>
            <Stack.Item className='tre-left-nav'>
              {!isTREAdminUser && (
                <WorkspaceLeftNav
                  workspaceServices={workspaceServices}
                  sharedServices={sharedServices}
                  setWorkspaceService={(ws: WorkspaceService) => setSelectedWorkspaceService(ws)}
                  addWorkspaceService={(ws: WorkspaceService) => addWorkspaceService(ws)} />
              )}
            </Stack.Item>
            <Stack.Item className='tre-body-content'>
              <Stack>
                <Stack.Item grow={100}>
                  <Routes>
                    <Route path="/" element={<>
                      <WorkspaceItem />
                      {!isTREAdminUser ? (
                        <WorkspaceServices workspaceServices={workspaceServices}
                          setWorkspaceService={(ws: WorkspaceService) => setSelectedWorkspaceService(ws)}
                          addWorkspaceService={(ws: WorkspaceService) => addWorkspaceService(ws)}
                          updateWorkspaceService={(ws: WorkspaceService) => updateWorkspaceService(ws)}
                          removeWorkspaceService={(ws: WorkspaceService) => removeWorkspaceService(ws)} />
                      ) : (
                        <Stack className="tre-panel">
                          <Stack.Item>
                            <FontIcon iconName="WarningSolid"
                              className={warningIcon}
                            />
                            You are currently accessing this workspace using a TRE Admin role. Additional funcitonality requires a workspace role, such as Workspace Owner.
                          </Stack.Item>
                        </Stack>
                      )}
                    </>}
                    />
                    {!isTREAdminUser && (
                      <>
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
                        <Route path="requests/*" element={
                          <Airlock />
                        } />
                      </>
                    )}
                  </Routes>
                </Stack.Item>
              </Stack>
            </Stack.Item>
          </Stack>
        </>
      );
    case LoadingState.Error:
    case LoadingState.AccessDenied:
      return (
        <ExceptionLayout e={apiError} />
      );
    default:
      return (
        <div style={{ marginTop: '20px' }}>
          <Spinner label="Loading Workspace" ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
        </div>
      );
  }
};

const { palette } = getTheme();
const warningIcon = mergeStyles({
  color: palette.orangeLight,
  fontSize: 18,
  marginRight: 8
});

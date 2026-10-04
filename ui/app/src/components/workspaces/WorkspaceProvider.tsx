import { FontIcon, Spinner, SpinnerSize, Stack, getTheme, mergeStyles } from "@fluentui/react";
import React, { useContext, useEffect, useRef, useState } from "react";
import { Route, Routes, useParams } from "react-router-dom";
import { ApiEndpoint } from "../../models/apiEndpoints";
import { WorkspaceService } from "../../models/workspaceService";
import { HttpMethod, ResultType, useAuthApiCall } from "../../hooks/useAuthApiCall";
import { WorkspaceHeader } from "./WorkspaceHeader";
import { WorkspaceItem } from "./WorkspaceItem";
import { WorkspaceLeftNav } from "./WorkspaceLeftNav";
import { WorkspaceServiceItem } from "./WorkspaceServiceItem";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { WorkspaceServices } from "./WorkspaceServices";
import { WorkspaceUsers } from "./WorkspaceUsers";
import { Workspace } from "../../models/workspace";
import { SharedService } from "../../models/sharedService";
import { SharedServices } from "../shared/SharedServices";
import { SharedServiceItem } from "../shared/SharedServiceItem";
import { Airlock } from "../shared/airlock/Airlock";
import { APIError, isRetryableApiError } from "../../models/exceptions";
import { LoadingState } from "../../models/loadingState";
import { ExceptionLayout } from "../shared/ExceptionLayout";
import { AppRolesContext } from "../../contexts/AppRolesContext";
import { RoleName, WorkspaceRoleName } from "../../models/roleNames";
import { useRefresh } from "../../hooks/useRefresh";
import { isEqualJson } from "../../utils/isEqualJson";

export const WorkspaceProvider: React.FunctionComponent = () => {
  const apiCall = useAuthApiCall();
  const [selectedWorkspaceService, setSelectedWorkspaceService] = useState({} as WorkspaceService);
  const [workspaceServices, setWorkspaceServices] = useState([] as Array<WorkspaceService>);
  const [sharedServices, setSharedServices] = useState([] as Array<SharedService>);
  const workspaceCtx = useRef(useContext(WorkspaceContext));
  const [wsRoles, setWSRoles] = useState([] as Array<string>);
  const [rolesWorkspaceId, setRolesWorkspaceId] = useState("");
  const [loadingState, setLoadingState] = useState(LoadingState.Loading);
  const [apiError, setApiError] = useState({} as APIError);
  const { workspaceId } = useParams();

  const appRoles = useContext(AppRolesContext);
  const [isTREAdminUser, setIsTREAdminUser] = useState(false);
  const [workspaceRefreshKey, setWorkspaceRefreshKey] = useState(0);
  const workspaceLoadPending = useRef(false);
  const refreshWorkspace = useRefresh(() => {
    if (!workspaceLoadPending.current) setWorkspaceRefreshKey((key) => key + 1);
  });
  const loadedWorkspaceId = useRef<string>();
  const canManageWorkspace =
    wsRoles.includes(WorkspaceRoleName.WorkspaceOwner) || appRoles.roles.includes(RoleName.TREAdmin);

  // set workspace context from url
  useEffect(() => {
    let active = true;
    workspaceLoadPending.current = true;
    if (loadedWorkspaceId.current !== workspaceId) {
      setLoadingState(LoadingState.Loading);
    }
    const getWorkspace = async () => {
      try {
        // get the workspace - first we get the scope_id so we can auth against the right aad app
        let scopeId = (await apiCall(`${ApiEndpoint.Workspaces}/${workspaceId}/scopeid`, HttpMethod.Get)).workspaceAuth
          .scopeId;
        if (!active) return;

        let authProvisioned: boolean = false;

        let wsRoles: Array<string> = [];
        let ws: Workspace = {} as Workspace;

        if (scopeId) {
          // use the client ID to get a token against the workspace (tokenOnly), and set the workspace roles in the context
          try {
            await apiCall(
              `${ApiEndpoint.Workspaces}/${workspaceId}`,
              HttpMethod.Get,
              scopeId,
              undefined,
              ResultType.JSON,
              (roles: Array<string>) => {
                wsRoles = roles;
              },
              true,
            );
            authProvisioned = true;
          } catch (e: any) {
            console.error("Authorization provisioning failed:", e);
            // On a background refresh keep the loaded workspace rather than switching to 403/admin-only mode.
            if (loadedWorkspaceId.current === workspaceId) return;
            authProvisioned = false;
          }
        }
        if (!active) return;

        if (authProvisioned && wsRoles && wsRoles.length > 0) {
          ws = (await apiCall(`${ApiEndpoint.Workspaces}/${workspaceId}`, HttpMethod.Get, scopeId)).workspace;
          if (!active) return;

          // get workspace services to pass to nav + ws services page
          const workspaceServices = await apiCall(
            `${ApiEndpoint.Workspaces}/${ws.id}/${ApiEndpoint.WorkspaceServices}`,
            HttpMethod.Get,
            ws.properties.scope_id,
          );
          if (!active) return;
          let sharedServices: SharedService[] = [];
          // Shared services are only shown to workspace owners and TRE Admins.
          if (wsRoles.includes(WorkspaceRoleName.WorkspaceOwner) || appRoles.roles.includes(RoleName.TREAdmin)) {
            sharedServices = (await apiCall(ApiEndpoint.SharedServices, HttpMethod.Get)).sharedServices;
          }
          if (!active) return;
          workspaceCtx.current.setWorkspace(ws);
          workspaceCtx.current.setRoles(wsRoles);
          setWSRoles((prev) => (isEqualJson(prev, wsRoles) ? prev : wsRoles));
          setRolesWorkspaceId(workspaceId || "");
          setWorkspaceServices((prev) =>
            isEqualJson(prev, workspaceServices.workspaceServices) ? prev : workspaceServices.workspaceServices,
          );
          setSharedServices((prev) => (isEqualJson(prev, sharedServices) ? prev : sharedServices));
          setIsTREAdminUser(false);
          loadedWorkspaceId.current = workspaceId;
          setLoadingState(LoadingState.Ok);
        } else if (appRoles.roles.includes(RoleName.TREAdmin)) {
          ws = (await apiCall(`${ApiEndpoint.Workspaces}/${workspaceId}`, HttpMethod.Get)).workspace;
          if (!active) return;
          workspaceCtx.current.setWorkspace(ws);
          workspaceCtx.current.setRoles([]);
          setWSRoles([]);
          setRolesWorkspaceId(workspaceId || "");
          setWorkspaceServices([]);
          setSharedServices([]);
          loadedWorkspaceId.current = workspaceId;
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
        if (!active) return;
        if (e.status === 401 || e.status === 403) {
          setApiError(e);
          setLoadingState(LoadingState.AccessDenied);
        } else if (loadedWorkspaceId.current !== workspaceId || !isRetryableApiError(e)) {
          // Keep the loaded workspace only for transient failures; e.g. a 404 after deletion shows the error.
          e.userMessage = "Error retrieving workspace";
          setApiError(e);
          setLoadingState(LoadingState.Error);
        }
      } finally {
        if (active) workspaceLoadPending.current = false;
      }
    };
    getWorkspace();
    return () => {
      active = false;
      workspaceLoadPending.current = false;
    };
  }, [apiCall, workspaceId, appRoles.roles, workspaceRefreshKey]);

  useEffect(() => {
    const ctx = workspaceCtx.current;
    return () => {
      ctx.setRoles([]);
      ctx.setWorkspace({} as Workspace);
      ctx.setCosts([]);
      loadedWorkspaceId.current = undefined;
    };
  }, [workspaceId]);

  useEffect(() => {
    let active = true;
    const getWorkspaceCosts = async () => {
      try {
        // TODO: amend when costs enabled in API for WorkspaceRoleName.Researcher
        if (rolesWorkspaceId === workspaceId && wsRoles.includes(WorkspaceRoleName.WorkspaceOwner)) {
          let scopeId = (await apiCall(`${ApiEndpoint.Workspaces}/${workspaceId}/scopeid`, HttpMethod.Get))
            .workspaceAuth.scopeId;
          const r = await apiCall(
            `${ApiEndpoint.Workspaces}/${workspaceId}/${ApiEndpoint.Costs}`,
            HttpMethod.Get,
            scopeId,
            undefined,
            ResultType.JSON,
          );
          const costs = [
            ...r.costs,
            ...r.workspace_services,
            ...r.workspace_services.flatMap((ws: { user_resources: any }) => [...ws.user_resources]),
          ];
          if (active) workspaceCtx.current.setCosts(costs);
        }
      } catch (e: any) {
        if (active) workspaceCtx.current.setCosts([]);
      }
    };

    getWorkspaceCosts();
    return () => {
      active = false;
    };
  }, [apiCall, workspaceId, rolesWorkspaceId, wsRoles]);

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
          <WorkspaceHeader />
          <Stack horizontal className="tre-body-inner">
            <Stack.Item className="tre-left-nav">
              <WorkspaceLeftNav
                workspaceServices={workspaceServices}
                sharedServices={sharedServices}
                setWorkspaceService={(ws: WorkspaceService) => setSelectedWorkspaceService(ws)}
                addWorkspaceService={(ws: WorkspaceService) => addWorkspaceService(ws)}
                isTREAdminUser={isTREAdminUser}
              />
            </Stack.Item>
            <Stack.Item className="tre-body-content">
              <Stack>
                <Stack.Item grow={100}>
                  <Routes>
                    <Route
                      path="/"
                      element={
                        <>
                          <WorkspaceItem onRefresh={refreshWorkspace} />
                          {!isTREAdminUser ? (
                            <WorkspaceServices
                              workspaceServices={workspaceServices}
                              setWorkspaceService={(ws: WorkspaceService) => setSelectedWorkspaceService(ws)}
                              addWorkspaceService={(ws: WorkspaceService) => addWorkspaceService(ws)}
                              updateWorkspaceService={(ws: WorkspaceService) => updateWorkspaceService(ws)}
                              removeWorkspaceService={(ws: WorkspaceService) => removeWorkspaceService(ws)}
                            />
                          ) : (
                            <Stack className="tre-panel">
                              <Stack.Item>
                                <FontIcon iconName="WarningSolid" className={warningIcon} />
                                You are currently accessing this workspace using the TRE Admin role. Additional
                                functionality requires a workspace role, such as Workspace Owner.
                              </Stack.Item>
                            </Stack>
                          )}
                        </>
                      }
                    />
                    {!isTREAdminUser && (
                      <>
                        <Route
                          path="workspace-services"
                          element={
                            <WorkspaceServices
                              workspaceServices={workspaceServices}
                              setWorkspaceService={(ws: WorkspaceService) => setSelectedWorkspaceService(ws)}
                              addWorkspaceService={(ws: WorkspaceService) => addWorkspaceService(ws)}
                              updateWorkspaceService={(ws: WorkspaceService) => updateWorkspaceService(ws)}
                              removeWorkspaceService={(ws: WorkspaceService) => removeWorkspaceService(ws)}
                              onRefresh={refreshWorkspace}
                            />
                          }
                        />
                        <Route
                          path="workspace-services/:workspaceServiceId/*"
                          element={
                            <WorkspaceServiceItem
                              workspaceService={selectedWorkspaceService}
                              updateWorkspaceService={(ws: WorkspaceService) => updateWorkspaceService(ws)}
                              removeWorkspaceService={(ws: WorkspaceService) => removeWorkspaceService(ws)}
                            />
                          }
                        />

                        {canManageWorkspace && (
                          <>
                            <Route path="shared-services" element={<SharedServices readonly={true} />} />
                            <Route
                              path="shared-services/:sharedServiceId/*"
                              element={<SharedServiceItem readonly={true} />}
                            />
                          </>
                        )}
                        <Route path="requests/*" element={<Airlock />} />
                      </>
                    )}
                    <Route path="users/*" element={<WorkspaceUsers />} />
                  </Routes>
                </Stack.Item>
              </Stack>
            </Stack.Item>
          </Stack>
        </>
      );
    case LoadingState.Error:
    case LoadingState.AccessDenied:
      return <ExceptionLayout e={apiError} onRetry={refreshWorkspace} />;
    default:
      return (
        <div style={{ marginTop: "20px" }}>
          <Spinner label="Loading Workspace" ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
        </div>
      );
  }
};

const { palette } = getTheme();
const warningIcon = mergeStyles({
  color: palette.orangeLight,
  fontSize: 18,
  marginRight: 8,
});

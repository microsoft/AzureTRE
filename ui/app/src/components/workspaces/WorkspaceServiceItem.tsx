import React, { useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { Route, Routes, useNavigate, useParams } from "react-router-dom";
import { ApiEndpoint } from "../../models/apiEndpoints";
import { useAuthApiCall, HttpMethod } from "../../hooks/useAuthApiCall";
import { UserResource } from "../../models/userResource";
import { WorkspaceService } from "../../models/workspaceService";
import { PrimaryButton, Spinner, SpinnerSize, Stack } from "@fluentui/react";
import { ComponentAction, Resource } from "../../models/resource";
import { ResourceCardList } from "../shared/ResourceCardList";
import { LoadingState } from "../../models/loadingState";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { ResourceType } from "../../models/resourceType";
import { ResourceHeader } from "../shared/ResourceHeader";
import { useComponentManager } from "../../hooks/useComponentManager";
import { CreateUpdateResourceContext } from "../../contexts/CreateUpdateResourceContext";
import { successStates } from "../../models/operation";
import { UserResourceItem } from "./UserResourceItem";
import { ResourceBody } from "../shared/ResourceBody";
import { SecuredByRole } from "../shared/SecuredByRole";
import { WorkspaceRoleName } from "../../models/roleNames";
import { APIError, isRetryableApiError } from "../../models/exceptions";
import { ExceptionLayout } from "../shared/ExceptionLayout";
import { CachedUser } from "../../models/user";
import { useAccount, useMsal } from "@azure/msal-react";
import { isOwnedByUser } from "../../models/userResource";
import { useRefresh } from "../../hooks/useRefresh";
import { isEqualJson } from "../../utils/isEqualJson";
import {
  nameSortOption,
  ResourceListControls,
  ResourceSortOption,
  statusSortOption,
  updatedSortOption,
  useResourceListFilter,
} from "../shared/ResourceListControls";

interface WorkspaceServiceItemProps {
  workspaceService?: WorkspaceService;
  updateWorkspaceService: (ws: WorkspaceService) => void;
  removeWorkspaceService: (ws: WorkspaceService) => void;
}

export const WorkspaceServiceItem: React.FunctionComponent<WorkspaceServiceItemProps> = (
  props: WorkspaceServiceItemProps,
) => {
  const { workspaceServiceId } = useParams();
  const [userResources, setUserResources] = useState([] as Array<UserResource>);
  const [workspaceService, setWorkspaceService] = useState({} as WorkspaceService);
  const [loadingState, setLoadingState] = useState(LoadingState.Loading);
  const [selectedUserResource, setSelectedUserResource] = useState({} as UserResource);
  const [hasUserResourceTemplates, setHasUserResourceTemplates] = useState(false);
  const [usersCache, setUsersCache] = useState(new Map<string, CachedUser>());
  const workspaceCtx = useContext(WorkspaceContext);
  const createFormCtx = useContext(CreateUpdateResourceContext);
  const navigate = useNavigate();
  const apiCall = useAuthApiCall();
  const [apiError, setApiError] = useState({} as APIError);
  const [showMyResources, setShowMyResources] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);
  const refresh = useRefresh(() => setRefreshKey((key) => key + 1));
  const { accounts } = useMsal();
  const account = useAccount(accounts[0] || {});

  const latestUpdate = useComponentManager(
    workspaceService,
    (r: Resource) => {
      props.updateWorkspaceService(r as WorkspaceService);
      setWorkspaceService(r as WorkspaceService);
    },
    (r: Resource) => {
      props.removeWorkspaceService(r as WorkspaceService);
      navigate(`/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.WorkspaceServices}`);
    },
  );
  const currentUserId =
    (account?.idTokenClaims as Record<string, unknown> | undefined)?.oid?.toString() ||
    account?.localAccountId.split(".")[0] ||
    "";
  const workspaceId = workspaceCtx.workspace.id;
  const workspaceScopeId = workspaceCtx.workspaceApplicationIdURI;
  const isWorkspaceOwner = workspaceCtx.roles.includes(WorkspaceRoleName.WorkspaceOwner);

  const getOwnerName = useCallback(
    (r: UserResource) =>
      usersCache.get(r.ownerId)?.displayName ||
      (r.ownerId && r.ownerId === currentUserId ? account?.name : undefined) ||
      r.ownerId ||
      "",
    [usersCache, currentUserId, account],
  );
  const sortOptions = useMemo<Array<ResourceSortOption<UserResource>>>(
    () => [
      nameSortOption<UserResource>(),
      { key: "owner", text: "Owner", compare: (a, b) => getOwnerName(a).localeCompare(getOwnerName(b)) },
      statusSortOption<UserResource>(),
      updatedSortOption<UserResource>(),
    ],
    [getOwnerName],
  );
  const extraSearchText = useCallback((r: UserResource) => [getOwnerName(r)], [getOwnerName]);
  // Only Workspace Owners see other users' resources, so the owner filter applies to them alone.
  const filterToMine = showMyResources && isWorkspaceOwner;
  const preFilter = useCallback(
    (r: UserResource) => !filterToMine || isOwnedByUser(r, currentUserId),
    [filterToMine, currentUserId],
  );
  const { visibleResources: displayedUserResources, controlsProps } = useResourceListFilter(userResources, {
    storageKey: "user-resource",
    sortOptions,
    extraSearchText,
    preFilter,
  });
  const [loadKey, setLoadKey] = useState(0);

  useEffect(() => {
    setLoadingState(LoadingState.Loading);
  }, [workspaceServiceId]);

  // Read the latest service passed from the parent without re-running the load when its identity changes.
  const passedWorkspaceService = useRef(props.workspaceService);
  passedWorkspaceService.current = props.workspaceService;

  const servicePath = `${ApiEndpoint.Workspaces}/${workspaceId}/${ApiEndpoint.WorkspaceServices}/${workspaceServiceId}`;
  // The service whose full load has completed; refreshes wait for it so they can't race the initial load.
  const fullyLoadedServicePath = useRef<string>();

  // Full load: the service, its user resources and whether it has user resource templates.
  useEffect(() => {
    if (!workspaceId) return;
    fullyLoadedServicePath.current = undefined;
    let cancelled = false;
    const getData = async () => {
      try {
        let svc = passedWorkspaceService.current;
        if (!svc || svc.id !== workspaceServiceId) {
          svc = (await apiCall(servicePath, HttpMethod.Get, workspaceScopeId)).workspaceService as WorkspaceService;
        }
        const [u, ut] = await Promise.all([
          apiCall(`${servicePath}/${ApiEndpoint.UserResources}`, HttpMethod.Get, workspaceScopeId),
          apiCall(
            `${ApiEndpoint.Workspaces}/${workspaceId}/${ApiEndpoint.WorkspaceServiceTemplates}/${svc.templateName}/${ApiEndpoint.UserResourceTemplates}`,
            HttpMethod.Get,
            workspaceScopeId,
          ),
        ]);
        if (cancelled) return;
        setWorkspaceService(svc);
        setHasUserResourceTemplates(!!(ut && ut.templates && ut.templates.length > 0));
        setUserResources(u.userResources);
        fullyLoadedServicePath.current = servicePath;
        setLoadingState(LoadingState.Ok);
      } catch (err: any) {
        if (cancelled) return;
        err.userMessage = "Error retrieving resources";
        setApiError(err);
        setLoadingState(LoadingState.Error);
      }
    };
    getData();
    return () => {
      cancelled = true;
    };
  }, [apiCall, servicePath, workspaceId, workspaceScopeId, workspaceServiceId, loadKey]);

  // Owner display names. Only owners see other users' resources, so only they need the user list.
  useEffect(() => {
    if (!workspaceId || !isWorkspaceOwner) {
      setUsersCache((prev) => (prev.size ? new Map() : prev));
      return;
    }
    let cancelled = false;
    const getUsers = async () => {
      try {
        const usersResponse = await apiCall(
          `${ApiEndpoint.Workspaces}/${workspaceId}/${ApiEndpoint.Users}`,
          HttpMethod.Get,
          workspaceScopeId,
        );
        const cache = new Map<string, CachedUser>();
        usersResponse.users?.forEach((user: any) => {
          cache.set(user.id, {
            displayName: user.displayName,
            email: user.email || user.userPrincipalName,
          });
        });
        if (!cancelled) setUsersCache(cache);
      } catch {
        if (!cancelled) setUsersCache(new Map());
      }
    };
    getUsers();
    return () => {
      cancelled = true;
    };
  }, [apiCall, workspaceId, workspaceScopeId, isWorkspaceOwner]);

  // Latest request parameters for refresh, read without re-running the refresh effect when they change.
  const refreshParams = useRef({ apiCall, servicePath, workspaceId, workspaceScopeId });
  refreshParams.current = { apiCall, servicePath, workspaceId, workspaceScopeId };

  // Manual and automatic refresh: re-read only the service and its user resources, keeping state when unchanged.
  useEffect(() => {
    const { apiCall, servicePath, workspaceId, workspaceScopeId } = refreshParams.current;
    if (refreshKey === 0 || !workspaceId || fullyLoadedServicePath.current !== servicePath) return;
    let cancelled = false;
    const refreshData = async () => {
      try {
        const [ws, u] = await Promise.all([
          apiCall(servicePath, HttpMethod.Get, workspaceScopeId),
          apiCall(`${servicePath}/${ApiEndpoint.UserResources}`, HttpMethod.Get, workspaceScopeId),
        ]);
        // Ignore the response if the user has since navigated to another service.
        if (cancelled || refreshParams.current.servicePath !== servicePath) return;
        setWorkspaceService((prev) => (isEqualJson(prev, ws.workspaceService) ? prev : ws.workspaceService));
        setUserResources((prev) => (isEqualJson(prev, u.userResources) ? prev : u.userResources));
      } catch (err: any) {
        if (cancelled || refreshParams.current.servicePath !== servicePath) return;
        if (isRetryableApiError(err)) {
          // Keep showing the last good data; the next refresh will try again.
          console.warn("Failed to refresh workspace service", err);
          return;
        }
        // Terminal errors (e.g. the service was deleted or access revoked) replace the stale view.
        err.userMessage = "Error retrieving resources";
        setApiError(err);
        setLoadingState(LoadingState.Error);
      }
    };
    refreshData();
    return () => {
      cancelled = true;
    };
  }, [refreshKey, refreshParams]);

  const addUserResource = (u: UserResource) => {
    let ur = [...userResources];
    ur.push(u);
    setUserResources(ur);
  };

  const updateUserResource = (u: UserResource) => {
    let ur = [...userResources];
    let i = ur.findIndex((f: UserResource) => f.id === u.id);
    ur.splice(i, 1, u);
    setUserResources(ur);
  };

  const removeUserResource = (u: UserResource) => {
    let ur = [...userResources];
    let i = ur.findIndex((f: UserResource) => f.id === u.id);
    ur.splice(i, 1);
    setUserResources(ur);
  };

  switch (loadingState) {
    case LoadingState.Ok:
      return (
        <>
          <Routes>
            <Route
              path="*"
              element={
                <>
                  <ResourceHeader resource={workspaceService} latestUpdate={latestUpdate} onRefresh={refresh} />
                  <ResourceBody resource={workspaceService} />
                  {hasUserResourceTemplates && (
                    <Stack className="tre-panel">
                      <Stack.Item>
                        <Stack horizontal horizontalAlign="space-between" verticalAlign="center">
                          <h1>Resources</h1>
                          <Stack horizontal verticalAlign="center" tokens={{ childrenGap: 8 }}>
                            <SecuredByRole
                              allowedWorkspaceRoles={[
                                WorkspaceRoleName.WorkspaceOwner,
                                WorkspaceRoleName.WorkspaceResearcher,
                                WorkspaceRoleName.AirlockManager,
                              ]}
                              element={
                                <PrimaryButton
                                  iconProps={{ iconName: "Add" }}
                                  text="Create new"
                                  disabled={
                                    !workspaceService.isEnabled ||
                                    latestUpdate.componentAction === ComponentAction.Lock ||
                                    successStates.indexOf(workspaceService.deploymentStatus) === -1
                                  }
                                  title={
                                    !workspaceService.isEnabled ||
                                    latestUpdate.componentAction === ComponentAction.Lock ||
                                    successStates.indexOf(workspaceService.deploymentStatus) === -1
                                      ? "Service must be enabled, successfully deployed, and not locked"
                                      : "Create a User Resource"
                                  }
                                  onClick={() => {
                                    createFormCtx.openCreateForm({
                                      resourceType: ResourceType.UserResource,
                                      resourceParent: workspaceService,
                                      onAdd: (r: Resource) => addUserResource(r as UserResource),
                                      workspaceApplicationIdURI: workspaceCtx.workspaceApplicationIdURI,
                                    });
                                  }}
                                />
                              }
                            />
                          </Stack>
                        </Stack>
                      </Stack.Item>
                      <Stack.Item>
                        <ResourceListControls
                          {...controlsProps}
                          searchPlaceholder="Search by name, owner or status..."
                          ariaLabel="Resource list controls"
                          showMine={showMyResources}
                          onShowMineChange={isWorkspaceOwner ? setShowMyResources : undefined}
                        />
                      </Stack.Item>
                      <Stack.Item>
                        {userResources && (
                          <ResourceCardList
                            resources={displayedUserResources}
                            selectResource={(r: Resource) => setSelectedUserResource(r as UserResource)}
                            updateResource={(r: Resource) => updateUserResource(r as UserResource)}
                            removeResource={(r: Resource) => removeUserResource(r as UserResource)}
                            emptyText={
                              controlsProps.search
                                ? `No resources found matching "${controlsProps.search}".`
                                : filterToMine
                                  ? "You do not own any resources in this workspace service."
                                  : "This workspace service contains no user resources."
                            }
                            isExposedExternally={workspaceService.properties.is_exposed_externally}
                            usersCache={usersCache}
                          />
                        )}
                      </Stack.Item>
                    </Stack>
                  )}
                </>
              }
            />
            <Route
              path="user-resources/:userResourceId/*"
              element={
                <UserResourceItem
                  userResource={selectedUserResource}
                  isExposedExternally={workspaceService.properties.is_exposed_externally}
                  updateUserResource={(u: UserResource) => updateUserResource(u)}
                  removeUserResource={(u: UserResource) => removeUserResource(u)}
                />
              }
            />
          </Routes>
        </>
      );
    case LoadingState.Error:
      return <ExceptionLayout e={apiError} onRetry={() => setLoadKey((key) => key + 1)} />;
    default:
      return (
        <div style={{ marginTop: "20px" }}>
          <Spinner
            label="Loading Workspace Service"
            ariaLive="assertive"
            labelPosition="top"
            size={SpinnerSize.large}
          />
        </div>
      );
  }
};

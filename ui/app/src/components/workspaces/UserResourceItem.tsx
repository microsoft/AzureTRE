import React, { useContext, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ApiEndpoint } from "../../models/apiEndpoints";
import { useAuthApiCall, HttpMethod } from "../../hooks/useAuthApiCall";
import { UserResource } from "../../models/userResource";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { ResourceHeader } from "../shared/ResourceHeader";
import { Resource } from "../../models/resource";
import { useComponentManager } from "../../hooks/useComponentManager";
import { ResourceBody } from "../shared/ResourceBody";
import { useRefresh } from "../../hooks/useRefresh";
import { APIError, isRetryableApiError } from "../../models/exceptions";
import { ExceptionLayout } from "../shared/ExceptionLayout";

interface UserResourceItemProps {
  userResource?: UserResource;
  isExposedExternally?: boolean;
  updateUserResource: (u: UserResource) => void;
  removeUserResource: (u: UserResource) => void;
}

export const UserResourceItem: React.FunctionComponent<UserResourceItemProps> = (props: UserResourceItemProps) => {
  const { workspaceServiceId, userResourceId } = useParams();
  const [userResource, setUserResource] = useState({} as UserResource);
  const [apiError, setApiError] = useState<APIError>();
  const loadedResourceId = useRef<string>();
  const apiCall = useAuthApiCall();
  const workspaceCtx = useContext(WorkspaceContext);
  const navigate = useNavigate();
  const [refreshKey, setRefreshKey] = useState(0);
  const refresh = useRefresh(() => setRefreshKey((key) => key + 1));

  const latestUpdate = useComponentManager(
    userResource,
    (r: Resource) => {
      props.updateUserResource(r as UserResource);
      setUserResource(r as UserResource);
    },
    (r: Resource) => {
      props.removeUserResource(r as UserResource);
      if (workspaceCtx.workspace.id)
        navigate(
          `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.WorkspaceServices}/${workspaceServiceId}`,
        );
    },
  );

  useEffect(() => {
    // Ignore responses for a previous route or refresh so they can't overwrite the current resource.
    let cancelled = false;
    const getData = async () => {
      // did we get passed the workspace service, or shall we get it from the api?
      const passedResource = props.userResource;
      if (!refreshKey && passedResource && passedResource.id === userResourceId) {
        loadedResourceId.current = passedResource.id;
        setUserResource(passedResource);
        setApiError(undefined);
      } else if (workspaceCtx.workspace.id) {
        try {
          let ur = await apiCall(
            `${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.WorkspaceServices}/${workspaceServiceId}/${ApiEndpoint.UserResources}/${userResourceId}`,
            HttpMethod.Get,
            workspaceCtx.workspaceApplicationIdURI,
          );
          if (cancelled) return;
          loadedResourceId.current = ur.userResource.id;
          setUserResource(ur.userResource);
          setApiError(undefined);
        } catch (e) {
          if (cancelled) return;
          // Keep the loaded resource only for transient failures; e.g. a 403/404 after access is revoked or the
          // resource is deleted replaces it with the error view.
          if (loadedResourceId.current === userResourceId && isRetryableApiError(e)) return;
          loadedResourceId.current = undefined;
          setUserResource({} as UserResource);
          setApiError(e as APIError);
        }
      }
    };
    getData();
    return () => {
      cancelled = true;
    };
  }, [
    apiCall,
    props.userResource,
    workspaceCtx.workspaceApplicationIdURI,
    userResourceId,
    workspaceServiceId,
    workspaceCtx.workspace.id,
    refreshKey,
  ]);

  return userResource && userResource.id === userResourceId ? (
    <>
      <ResourceHeader
        resource={userResource}
        latestUpdate={latestUpdate}
        isExposedExternally={props.isExposedExternally}
        onRefresh={refresh}
      />
      <ResourceBody resource={userResource} />
    </>
  ) : apiError ? (
    <ExceptionLayout e={apiError} onRetry={refresh} />
  ) : (
    <></>
  );
};

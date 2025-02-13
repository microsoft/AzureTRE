import React, { useContext, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ApiEndpoint } from "../../models/apiEndpoints";
import { useAuthApiCall, HttpMethod } from "../../hooks/useAuthApiCall";
import { UserResource } from "../../models/userResource";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { ResourceHeader } from "../shared/ResourceHeader";
import { Resource } from "../../models/resource";
import { useComponentManager } from "../../hooks/useComponentManager";
import { ResourceBody } from "../shared/ResourceBody";

interface UserResourceItemProps {
  userResource?: UserResource;
  updateUserResource: (u: UserResource) => void;
  removeUserResource: (u: UserResource) => void;
}

export const UserResourceItem: React.FunctionComponent<
  UserResourceItemProps
> = (props: UserResourceItemProps) => {
  const { workspaceServiceId, userResourceId } = useParams();
  const [userResource, setUserResource] = useState({} as UserResource);
  const apiCall = useAuthApiCall();
  const workspaceCtx = useContext(WorkspaceContext);
  const navigate = useNavigate();

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
    const getData = async () => {
      // did we get passed the workspace service, or shall we get it from the api?
      if (props.userResource && props.userResource.id) {
        setUserResource(props.userResource);
      } else if (workspaceCtx.workspace.id) {
        let ur = await apiCall(
          `${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.WorkspaceServices}/${workspaceServiceId}/${ApiEndpoint.UserResources}/${userResourceId}`,
          HttpMethod.Get,
          workspaceCtx.workspaceApplicationIdURI,
        );
        setUserResource(ur.userResource);
      }
    };
    getData();
  }, [
    apiCall,
    props.userResource,
    workspaceCtx.workspaceApplicationIdURI,
    userResourceId,
    workspaceServiceId,
    workspaceCtx.workspace.id,
  ]);

  return userResource && userResource.id ? (
    <>
      <ResourceHeader resource={userResource} latestUpdate={latestUpdate} />
      <ResourceBody resource={userResource} />
    </>
  ) : (
    <></>
  );
};

import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { Workspace } from '../../models/workspace';
import { useAuthApiCall, HttpMethod } from '../../useAuthApiCall';
import { UserResource } from '../../models/userResource';
import { ResourceDebug } from './ResourceDebug';

// TODO:
// - This 'page' might die in place of a card on the Workspace services page - leave it alone for now

interface UserResourceItemProps {
  workspace: Workspace,
  userResource?: UserResource
}

export const UserResourceItem: React.FunctionComponent<UserResourceItemProps> = (props: UserResourceItemProps) => {
  const { workspaceServiceId, userResourceId } = useParams();
  const [userResource, setUserResource] = useState({} as UserResource)
  const apiCall = useAuthApiCall();

  useEffect(() => {
    const getData = async () => {
      // did we get passed the workspace service, or shall we get it from the api? 
      if (props.userResource && props.userResource.id) {
        setUserResource(props.userResource);
      } else {
        let ur = await apiCall(`${ApiEndpoint.Workspaces}/${props.workspace.id}/${ApiEndpoint.WorkspaceServices}/${workspaceServiceId}/${ApiEndpoint.UserResources}/${userResourceId}`, HttpMethod.Get, props.workspace.properties.app_id);
        setUserResource(ur.userResource);
      }
    };
    getData();
  }, [apiCall, props.userResource, props.workspace.id, props.workspace.properties.app_id, userResourceId, workspaceServiceId]);

  return (
    <>
      <h1>User Resource: {userResource.properties?.display_name}</h1>

      <ResourceDebug resource={userResource} />
    </>
  );
};

import React, { useContext, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { useAuthApiCall, HttpMethod } from '../../useAuthApiCall';
import { UserResource } from '../../models/userResource';
import { ResourceDebug } from '../shared/ResourceDebug';
import { ResourcePropertyPanel } from '../shared/ResourcePropertyPanel';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';

// TODO:
// - This 'page' might die in place of a card on the Workspace services page - leave it alone for now

interface UserResourceItemProps {
  userResource?: UserResource
}

export const UserResourceItem: React.FunctionComponent<UserResourceItemProps> = (props: UserResourceItemProps) => {
  const { workspaceServiceId, userResourceId } = useParams();
  const [userResource, setUserResource] = useState({} as UserResource)
  const apiCall = useAuthApiCall();
  const workspaceCtx = useContext(WorkspaceContext);

  useEffect(() => {
    const getData = async () => {
      // did we get passed the workspace service, or shall we get it from the api? 
      if (props.userResource && props.userResource.id) {
        setUserResource(props.userResource);
      } else {
        let ur = await apiCall(`${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.WorkspaceServices}/${workspaceServiceId}/${ApiEndpoint.UserResources}/${userResourceId}`, HttpMethod.Get, workspaceCtx.workspaceClientId);
        setUserResource(ur.userResource);
      }
    };
    getData();
  }, [apiCall, props.userResource, workspaceCtx.workspaceClientId, userResourceId, workspaceServiceId, workspaceCtx.workspace.id]);

  return (
    <>
      <h1>User Resource: {userResource.properties?.display_name}</h1>
      { userResource && userResource.id &&
        <ResourcePropertyPanel resource={userResource}/>
      }
      <ResourceDebug resource={userResource} />
    </>
  );
};

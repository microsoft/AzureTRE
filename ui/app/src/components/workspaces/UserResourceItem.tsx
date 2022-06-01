import React, { useContext, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { useAuthApiCall, HttpMethod } from '../../hooks/useAuthApiCall';
import { UserResource } from '../../models/userResource';
import { ResourceDebug } from '../shared/ResourceDebug';
import { ResourcePropertyPanel } from '../shared/ResourcePropertyPanel';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import { Pivot, PivotItem } from '@fluentui/react';
import { ResourceHistory } from '../shared/ResourceHistory';
import { ResourceHeader } from '../shared/ResourceHeader';
import { Resource } from '../../models/resource';
import { useComponentManager } from '../../hooks/useComponentManager';
import { ResourceOperationsList } from '../shared/ResourceOperationsList';

interface UserResourceItemProps {
  userResource?: UserResource
}

export const UserResourceItem: React.FunctionComponent<UserResourceItemProps> = (props: UserResourceItemProps) => {
  const { workspaceServiceId, userResourceId } = useParams();
  const [userResource, setUserResource] = useState({} as UserResource)
  const apiCall = useAuthApiCall();
  const workspaceCtx = useContext(WorkspaceContext);
  const componentAction = useComponentManager(userResource, (r: Resource) => setUserResource(r as UserResource));

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
    userResource && userResource.id ?
      <>
        <ResourceHeader resource={userResource} componentAction={componentAction} />
        <Pivot aria-label="User Resource Menu" className='tre-panel'>
          <PivotItem
            headerText="Overview"
            headerButtonProps={{
              'data-order': 1,
              'data-title': 'Overview',
            }}
          >
            <ResourcePropertyPanel resource={userResource} />
            <ResourceDebug resource={userResource} />
          </PivotItem>
          <PivotItem headerText="History">
            <ResourceHistory history={userResource.history} />
          </PivotItem>
          <PivotItem headerText="Operations">
            <ResourceOperationsList resource={userResource} />
          </PivotItem>
        </Pivot>
      </>
      : <></>
  );
};

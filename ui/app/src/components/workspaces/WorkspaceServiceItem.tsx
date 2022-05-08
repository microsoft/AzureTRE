import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { Workspace } from '../../models/workspace';
import { useAuthApiCall, HttpMethod } from '../../useAuthApiCall';
import { UserResource } from '../../models/userResource';
import { WorkspaceService } from '../../models/workspaceService';
import { ResourceDebug } from './ResourceDebug';

// TODO:
// - replace list of user resources with cards
// - loading placeholders / error management

interface WorkspaceServiceItemProps {
  workspace: Workspace,
  workspaceService?: WorkspaceService,
  setUserResource: (userResource: UserResource) => void
}

export const WorkspaceServiceItem: React.FunctionComponent<WorkspaceServiceItemProps> = (props: WorkspaceServiceItemProps) => {
  const { workspaceServiceId } = useParams();
  const [userResources, setUserResources] = useState([{} as UserResource])
  const [workspaceService, setWorkspaceService] = useState({} as WorkspaceService)
  const apiCall = useAuthApiCall();

  useEffect(() => {
    const getData = async () => {
      // did we get passed the workspace service, or shall we get it from the api? 
      if (props.workspaceService && props.workspaceService.id) {
        setWorkspaceService(props.workspaceService);
      } else {
        let ws = await apiCall(`${ApiEndpoint.Workspaces}/${props.workspace.id}/${ApiEndpoint.WorkspaceServices}/${workspaceServiceId}`, HttpMethod.Get, props.workspace.properties.app_id);
        setWorkspaceService(ws.workspaceService);
      }

      // get the user resources
      const u = await apiCall(`${ApiEndpoint.Workspaces}/${props.workspace.id}/${ApiEndpoint.WorkspaceServices}/${workspaceServiceId}/${ApiEndpoint.UserResources}`, HttpMethod.Get, props.workspace.properties.app_id)
      setUserResources(u.userResources);
    };
    getData();
  }, [apiCall, props.workspace.id, props.workspace.properties.app_id, props.workspaceService, workspaceServiceId]);

  return (
    <>
      <h1>{workspaceService.properties?.display_name}</h1>

      <h2>User Resources:</h2>
      {
        userResources &&
        <ul>
          {
            userResources.map((userResource, i) => {
              return (
                <li key={i}>
                  <Link to={`user-resources/${userResource.id}`} onClick={() => props.setUserResource(userResource)}>{userResource.properties?.display_name}</Link>
                </li>
              )
            })
          }
        </ul>
      }

      <ResourceDebug resource={workspaceService} />
    </>
  );
};

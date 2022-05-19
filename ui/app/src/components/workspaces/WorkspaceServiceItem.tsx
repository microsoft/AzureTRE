import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { Workspace } from '../../models/workspace';
import { useAuthApiCall, HttpMethod } from '../../useAuthApiCall';
import { UserResource } from '../../models/userResource';
import { WorkspaceService } from '../../models/workspaceService';
import { ResourceDebug } from '../shared/ResourceDebug';
import { MessageBar, MessageBarType, Spinner, SpinnerSize } from '@fluentui/react';
import { ResourcePropertyPanel } from '../shared/ResourcePropertyPanel';
import { Resource } from '../../models/resource';
import { ResourceCardList } from '../shared/ResourceCardList';

// TODO:
// - separate loading placeholders for user resources instead of spinner

interface WorkspaceServiceItemProps {
  workspace: Workspace,
  workspaceService?: WorkspaceService,
  setUserResource: (userResource: UserResource) => void
}

export const WorkspaceServiceItem: React.FunctionComponent<WorkspaceServiceItemProps> = (props: WorkspaceServiceItemProps) => {
  const { workspaceServiceId } = useParams();
  const [userResources, setUserResources] = useState([{} as UserResource])
  const [workspaceService, setWorkspaceService] = useState({} as WorkspaceService)
  const [loadingState, setLoadingState] = useState('loading');
  const apiCall = useAuthApiCall();

  useEffect(() => {
    const getData = async () => {
      try {
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
        setLoadingState('ok');
      } catch {
        setLoadingState('error');
      }
    };
    getData();
  }, [apiCall, props.workspace.id, props.workspace.properties.app_id, props.workspaceService, workspaceServiceId]);

  switch (loadingState) {
    case 'ok':
      return (
        <>
          <h1>{workspaceService.properties?.display_name}</h1>
          <ResourcePropertyPanel resource={workspaceService}/>
          <h2>User Resources:</h2>
          {
            userResources &&
            <ResourceCardList
              resources={userResources}
              selectResource={(r: Resource) => props.setUserResource(r as UserResource)}
              emptyText="This workspace service contains no user resources." />
          }
          <ResourceDebug resource={workspaceService} />
        </>
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
      );
    default:
      return (
        <div style={{ marginTop: '20px' }}>
          <Spinner label="Loading Workspace Service" ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
        </div>
      )
  }
};

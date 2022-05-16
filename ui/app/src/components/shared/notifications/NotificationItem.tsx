import React, { useEffect, useState } from 'react';
import { ApiEndpoint } from '../../../models/apiEndpoints';
import { Operation } from '../../../models/operation';
import { Workspace } from '../../../models/workspace';
import { HttpMethod, useAuthApiCall } from '../../../useAuthApiCall';
import { useInterval } from './useInterval';
import config from '../../../config.json';
import { ProgressIndicator } from '@fluentui/react';
import { Resource } from '../../../models/resource';

interface NotificationItemProps {
  operation: Operation
}

export const NotificationItem: React.FunctionComponent<NotificationItemProps> = (props: NotificationItemProps) => {
  const apiCall = useAuthApiCall();
  const [workspace, setWorkspace] = useState({} as Workspace);
  const [operation, setOperation] = useState(props.operation);
  const [resource, setResource] = useState({} as Resource);

  useEffect(() => {
    let workspaceAuth = false;
    let isWs = false;

    const getOperation = async () => {
      if (props.operation.resourcePath.indexOf(ApiEndpoint.Workspaces) !== -1) {
        // we need the workspace to get auth details
        workspaceAuth = true;
        const wsId = props.operation.resourcePath.split('/')[2];
        const ws = (await apiCall(`${ApiEndpoint.Workspaces}/${wsId}`, HttpMethod.Get)).workspace;
        setWorkspace(ws);

        if (props.operation.resourcePath.split('/').length === 3) {
          isWs = true;
          setResource(ws);
        }

        if (!isWs) {
          let r = await apiCall(props.operation.resourcePath, HttpMethod.Get, workspaceAuth ? ws.properties.app_id : null);
          if (r['userResource']) setResource(r.userResource);
          if (r['workspaceService']) setResource(r.workspaceService);
          if (r['sharedService']) setResource(r.sharedService);
        }
      }
    }
    getOperation();
  }, [apiCall, props.operation.id, props.operation.resourcePath]);


  useInterval(async () => {
    if (!workspace || !workspace.id) return;
    let op = (await apiCall(`${props.operation.resourcePath}/${ApiEndpoint.Operations}/${props.operation.id}`, HttpMethod.Get, workspace.properties.app_id)).operation
    console.log("polling operation...");
    setOperation(op);
  }, config.pollingDelayMilliseconds);

  return (
    resource && resource.id ?
      <li>
        <ProgressIndicator 
          label={`${resource.properties.display_name}: ${operation.action}`} 
          description={`${resource.resourceType} is ${operation.status}`} />
      </li>
      :
      <>shimmer</>
  );
};

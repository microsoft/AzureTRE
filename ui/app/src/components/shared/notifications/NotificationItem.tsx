import React, { useEffect, useState } from 'react';
import { ApiEndpoint } from '../../../models/apiEndpoints';
import { Operation } from '../../../models/operation';
import { Workspace } from '../../../models/workspace';
import { HttpMethod, useAuthApiCall } from '../../../useAuthApiCall';
import { useInterval } from './useInterval';
import config from '../../../config.json';
import { Spinner, SpinnerSize } from '@fluentui/react';

interface NotificationItemProps {
  operation: Operation
}

export const NotificationItem: React.FunctionComponent<NotificationItemProps> = (props: NotificationItemProps) => {
  const apiCall = useAuthApiCall();
  const [workspace, setWorkspace] = useState({} as Workspace)
  const [operation, setOperation] = useState(props.operation);

  useEffect(() => {
    const getOperation = async() => {
      const wsId = props.operation.resourcePath.split('/')[2];
      console.log(wsId);
      const ws = (await apiCall(`${ApiEndpoint.Workspaces}/${wsId}`, HttpMethod.Get)).workspace;
      setWorkspace(ws);
      }
    getOperation();
  }, [apiCall, props.operation.id, props.operation.resourcePath]);

  
    useInterval(async() => {
      if (!workspace || !workspace.id) return;
      let op = (await apiCall(`${props.operation.resourcePath}/${ApiEndpoint.Operations}/${props.operation.id}`, HttpMethod.Get, workspace.properties.app_id)).operation
      console.log("polling operation...");
      setOperation(op);
    }, config.pollingDelayMilliseconds);

  return (
    <li>
      <Spinner size={SpinnerSize.large} />
      {operation.action} - {operation.status}
    </li>
  );
};

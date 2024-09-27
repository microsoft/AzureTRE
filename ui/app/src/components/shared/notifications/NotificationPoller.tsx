import React from 'react';
import { useInterval } from './useInterval';
import { HttpMethod, useAuthApiCall } from '../../../hooks/useAuthApiCall';
import { ApiEndpoint } from '../../../models/apiEndpoints';
import { TRENotification } from '../../../models/treNotification';
import { Operation } from '../../../models/operation';
import config from '../../../config.json';

interface NotificationPollerProps {
  notification: TRENotification,
  updateOperation: (n: Operation) => void
}

export const NotificationPoller: React.FunctionComponent<NotificationPollerProps> = (props: NotificationPollerProps) => {
  const apiCall = useAuthApiCall();

  useInterval(async () => {

    try {
      let op = (await apiCall(`${props.notification.operation.resourcePath}/${ApiEndpoint.Operations}/${props.notification.operation.id}`,
        HttpMethod.Get, props.notification.workspace ? props.notification.workspace.properties.scope_id: null)).operation as Operation;

      // check if any fields have changed - ie the json is any different. we don't care _what_ has changed, just that something has
      if (JSON.stringify(op) !== JSON.stringify(props.notification.operation)) {
        props.notification.operation = op;
        props.updateOperation(op);
      }
    } catch (e: any) {
      // likely that the user no longer has access to the operation due to a role change
      config.debug && console.log(`Operation ${props.notification.operation.id} for ${props.notification.operation.resourcePath} cqnnot be retrieved`);
    }
  }, config.pollingDelayMilliseconds);

  return (<></>);
};

import React, { useEffect } from 'react';
import { useInterval } from './useInterval';
import { HttpMethod, useAuthApiCall } from '../../../useAuthApiCall';
import { ApiEndpoint } from '../../../models/apiEndpoints';
import { TRENotification } from '../../../models/treNotification';
import { Operation } from '../../../models/operation';

interface NotificationPollerProps {
  notification: TRENotification,
  updateNotification: (n: TRENotification) => void
}

export const NotificationPoller: React.FunctionComponent<NotificationPollerProps> = (props: NotificationPollerProps) => {
  const apiCall = useAuthApiCall();

  useInterval(async () => {
    let op = (await apiCall(`${props.notification.operation.resourcePath}/${ApiEndpoint.Operations}/${props.notification.operation.id}`, HttpMethod.Get, props.notification.workspace ? props.notification.workspace.properties.app_id : null)).operation as Operation;

    // check if any fields have changed - ie the json is any different. we don't care _what_ has changed, just that something has
    if (JSON.stringify(op) !== JSON.stringify(props.notification.operation)) {
      props.notification.operation = op;
      props.updateNotification(props.notification);
    }
  }, 5000);

  return (<></>);
};

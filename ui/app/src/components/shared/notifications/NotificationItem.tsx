import React, {  } from 'react';
import { ProgressIndicator } from '@fluentui/react';
import { TRENotification } from '../../../models/treNotification';

interface NotificationItemProps {
  notification: TRENotification
}

export const NotificationItem: React.FunctionComponent<NotificationItemProps> = (props: NotificationItemProps) => {
 
  return (
      <li>
        <ProgressIndicator
          label={`${props.notification.resource.properties.display_name}: ${props.notification.operation.action}`} 
          description={`${props.notification.resource.resourceType} is ${props.notification.operation.status}`} />
      </li>
  );
};

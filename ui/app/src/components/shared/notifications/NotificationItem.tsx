import React, { useState } from 'react';
import { Icon, ProgressIndicator } from '@fluentui/react';
import { TRENotification } from '../../../models/treNotification';
import { failedStates, inProgressStates } from '../../../models/operation';
import { Link } from 'react-router-dom';
import moment from 'moment';
import { useInterval } from './useInterval';

interface NotificationItemProps {
  notification: TRENotification
}

export const NotificationItem: React.FunctionComponent<NotificationItemProps> = (props: NotificationItemProps) => {
  const [now, setNow] = useState(moment.utc());

  const getRelativeTime = (createdWhen: number) => {
    return (moment.utc(moment.unix(createdWhen))).from(now);
  }

  // update the 'now' time for comparison - only while the item is rendered (panel is open)
  useInterval(() => {
    setNow(moment.utc());
  }, 10000)

  return (
    <li className="tre-notification-item">
      {
        inProgressStates.includes(props.notification.operation.status) ?
          <ProgressIndicator
            barHeight={4}
            label={<Link style={{ textDecoration: 'none', fontWeight: 'bold', color: 'blue' }} to={props.notification.operation.resourcePath}>
              {props.notification.resource.properties.display_name}: {props.notification.operation.action}
            </Link>}
            description={`${props.notification.resource.resourceType} is ${props.notification.operation.status}`} />
          :
          <ProgressIndicator
            barHeight={4}
            percentComplete={100}
            label={
              <Link style={{ textDecoration: 'none', fontWeight: 'bold', color: 'blue' }} to={props.notification.operation.resourcePath}>
                <Icon iconName={failedStates.includes(props.notification.operation.status) ? 'ErrorBadge' : 'SkypeCheck'} style={{ position: 'relative', top: '2px', color: 'green', marginRight: '10px' }} />
                {props.notification.resource.properties.display_name}: {props.notification.operation.action}
              </Link>
            }
            description={`${props.notification.resource.resourceType} is ${props.notification.operation.status}`} />
      }

      <div className="tre-notification-time">{getRelativeTime(props.notification.operation.createdWhen)}</div>
    </li>
  );
};

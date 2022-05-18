import React, { useState } from 'react';
import { Icon, ProgressIndicator, Link as FluentLink, Stack } from '@fluentui/react';
import { TRENotification } from '../../../models/treNotification';
import { completedStates, failedStates, inProgressStates, OperationStep } from '../../../models/operation';
import { Link } from 'react-router-dom';
import moment from 'moment';
import { useInterval } from './useInterval';
import { isNoSubstitutionTemplateLiteral } from 'typescript';
import { relative } from 'path';

interface NotificationItemProps {
  notification: TRENotification
}

export const NotificationItem: React.FunctionComponent<NotificationItemProps> = (props: NotificationItemProps) => {
  const [now, setNow] = useState(moment.utc());
  const [isExpanded, setIsExpanded] = useState(false);

  const getRelativeTime = (createdWhen: number) => {
    return (moment.utc(moment.unix(createdWhen))).from(now);
  }

  // update the 'now' time for comparison - only while the item is rendered (panel is open)
  useInterval(() => {
    setNow(moment.utc());
  }, 10000)

  const getIconAndColourForStatus = (status: string) => {
    if (failedStates.includes(status)) return ['ErrorBadge', 'red'];
    if (completedStates.includes(status)) return ['SkypeCheck', 'green'];
    if (status === "not_deployed") return ['Clock', '#cccccc'];
    return ['ProgressLoopInner', 'blue'];
  }

  return (
    <li className="tre-notification-item">
      {
        inProgressStates.includes(props.notification.operation.status) ?
          <>
            <ProgressIndicator
              barHeight={4}
              label={<Link style={{ textDecoration: 'none', fontWeight: 'bold', color: 'blue' }} to={props.notification.operation.resourcePath}>
                {props.notification.resource.properties.display_name}: {props.notification.operation.action}
              </Link>}
              description={`${props.notification.resource.resourceType} is ${props.notification.operation.status}`} />
          </>
          :
          <ProgressIndicator
            barHeight={4}
            percentComplete={100}
            label={
              <Link style={{ textDecoration: 'none', fontWeight: 'bold', color: 'blue' }} to={props.notification.operation.resourcePath}>
                <Icon iconName={getIconAndColourForStatus(props.notification.operation.status)[0]} style={{ color: getIconAndColourForStatus(props.notification.operation.status)[1], position: 'relative', top: '2px', marginRight: '10px' }} />
                {props.notification.resource.properties.display_name}: {props.notification.operation.action}
              </Link>
            }
            description={`${props.notification.resource.resourceType} is ${props.notification.operation.status}`} />
      }
      <Stack horizontal style={{ marginTop: '10px' }}>
        <Stack.Item grow={5}>
          {
            props.notification.operation.steps && props.notification.operation.steps.length > 0 && !(props.notification.operation.steps.length === 1 && props.notification.operation.steps[0].stepId === 'main') ?
              <FluentLink title={isExpanded ? 'Show less' : 'Show more'} href="#" onClick={() => { setIsExpanded(!isExpanded) }} style={{ position: 'relative', top: '2px' }}>{isExpanded ? <Icon iconName='ChevronUp' aria-label='Expand Steps' /> : <Icon iconName='ChevronDown' aria-label='Collapse Steps' />}</FluentLink>
              :
              ' '
          }
        </Stack.Item>
        <Stack.Item> <div className="tre-notification-time">{getRelativeTime(props.notification.operation.createdWhen)}</div></Stack.Item>
      </Stack>

      {
        isExpanded &&
        <>
          <ul className="tre-notifications-steps-list">
            {props.notification.operation.steps && props.notification.operation.steps.map((s: OperationStep, i: number) => {
              return (
                <li key={i}>
                  <Icon iconName={getIconAndColourForStatus(s.status)[0]} style={{ color: getIconAndColourForStatus(s.status)[1], position: 'relative', top: '2px', marginRight: '10px' }} />
                  {
                    s.stepId === "main" ?
                      <>{props.notification.resource.properties.display_name}: {props.notification.operation.action}</> :
                      s.stepTitle
                  }
                </li>)
            })
            }
          </ul>
        </>
      }
    </li>
  );
};

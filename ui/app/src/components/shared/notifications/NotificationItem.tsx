import React, { useEffect, useState } from 'react';
import { Icon, ProgressIndicator, Link as FluentLink, Stack, DefaultPalette, Shimmer, ShimmerElementType } from '@fluentui/react';
import { TRENotification } from '../../../models/treNotification';
import { awaitingStates, completedStates, failedStates, inProgressStates, Operation, OperationStep } from '../../../models/operation';
import { Link } from 'react-router-dom';
import moment from 'moment';
import { useInterval } from './useInterval';
import { HttpMethod, useAuthApiCall } from '../../../hooks/useAuthApiCall';
import { ApiEndpoint } from '../../../models/apiEndpoints';
import { getResourceFromResult, Resource } from '../../../models/resource';
import { NotificationPoller } from './NotificationPoller';
import { APIError } from '../../../models/exceptions';
import { ExceptionLayout } from '../ExceptionLayout';
import { addUpdateOperation } from './operationsSlice';
import { useAppDispatch } from '../../../hooks/customReduxHooks';

interface NotificationItemProps {
  operation: Operation,
  showCallout: (o: Operation, r: Resource) => void
}

export const NotificationItem: React.FunctionComponent<NotificationItemProps> = (props: NotificationItemProps) => {
  const [now, setNow] = useState(moment.utc());
  const [isExpanded, setIsExpanded] = useState(false);
  const [notification, setNotification] = useState({} as TRENotification);
  const [loadingNotification, setLoadingNotification] = useState(true);
  const [errorNotification, setErrorNotification] = useState(false);
  const dispatch = useAppDispatch();

  const apiCall = useAuthApiCall();
  const [apiError, setApiError] = useState({} as APIError);

  const getRelativeTime = (createdWhen: number) => {
    return (moment.utc(moment.unix(createdWhen))).from(now);
  }

  useEffect(() => {
    const setupNotification = async (op: Operation) => {
      // ignore if we've already set this operation up
      if (notification.resource) return;

      let isWs = false;
      let ws = null;
      let resource = null;

      try {
        if (op.resourcePath.indexOf(ApiEndpoint.Workspaces) !== -1) {
          // we need the workspace to get auth details
          const wsId = op.resourcePath.split('/')[2];
          ws = (await apiCall(`${ApiEndpoint.Workspaces}/${wsId}`, HttpMethod.Get)).workspace;

          if (op.resourcePath.split('/').length === 3) {
            isWs = true;
            resource = ws;
          }

          if (!isWs) {
            let r = await apiCall(op.resourcePath, HttpMethod.Get, ws.properties.scope_id);
            resource = getResourceFromResult(r);
          }
        } else {
          let r = await apiCall(op.resourcePath, HttpMethod.Get);
          resource = getResourceFromResult(r);
        }
        setNotification({ operation: op, resource: resource, workspace: ws });
      } catch (err: any) {
        err.userMessage = `Error retrieving operation details for ${props.operation.id}`
        setApiError(err);
        setErrorNotification(true);
      }
      setLoadingNotification(false);
    }

    setupNotification(props.operation);

  }, [props.operation, apiCall, notification.resource]);

  // update the 'now' time for comparison
  useInterval(() => {
    setNow(moment.utc());
  }, 10000);

  const getIconAndColourForStatus = (status: string) => {
    if (failedStates.includes(status)) return ['ErrorBadge', 'red'];
    if (completedStates.includes(status)) return ['SkypeCheck', 'green'];
    if (awaitingStates.includes(status)) return ['Clock', '#cccccc'];
    return ['ProgressLoopInner', DefaultPalette.themePrimary];
  }

  const updateOperation = (operation: Operation) => {
    dispatch(addUpdateOperation(operation));
    if (completedStates.includes(operation.status)) {
      props.showCallout(operation, notification.resource);
    }
  }

  return (
    <>
      {
        props.operation.dismiss ? <></> :
          loadingNotification ?
            <li>
              <Shimmer shimmerElements={[{ type: ShimmerElementType.gap, width: '100%' }]} />
              <Shimmer width="50%" />
              <Shimmer shimmerElements={[{ type: ShimmerElementType.gap, width: '100%' }]} />
              <Shimmer />
              <Shimmer shimmerElements={[{ type: ShimmerElementType.gap, width: '100%' }]} />
              <Shimmer />
            </li>
            :
            errorNotification ?
              <li>
                <ExceptionLayout e={apiError} />
              </li>
              :
              <li className="tre-notification-item">

                {
                  inProgressStates.indexOf(props.operation.status) !== -1 &&
                  <NotificationPoller notification={notification} updateOperation={(operation: Operation) => updateOperation(operation)} />
                }

                <ProgressIndicator
                  barHeight={4}
                  percentComplete={awaitingStates.includes(props.operation.status) ? 0 : completedStates.includes(props.operation.status) ? 100 : undefined}
                  label={<Link style={{ textDecoration: 'none', fontWeight: 'bold', color: DefaultPalette.themePrimary }} to={props.operation.resourcePath}>
                    <Icon iconName={getIconAndColourForStatus(props.operation.status)[0]} style={{ color: getIconAndColourForStatus(props.operation.status)[1], position: 'relative', top: '2px', marginRight: '10px' }} />
                    {notification.resource.properties.display_name}: {props.operation.action}
                  </Link>}
                  description={`${notification.resource.resourceType} is ${props.operation.status}`} />

                <Stack horizontal style={{ marginTop: '10px' }}>
                  <Stack.Item grow={5}>
                    {
                      props.operation.steps && props.operation.steps.length > 0 && !(props.operation.steps.length === 1 && props.operation.steps[0].stepId === 'main') ?
                        <FluentLink title={isExpanded ? 'Show less' : 'Show more'} href="#" onClick={() => { setIsExpanded(!isExpanded) }} style={{ position: 'relative', top: '2px' }}>{isExpanded ? <Icon iconName='ChevronUp' aria-label='Expand Steps' /> : <Icon iconName='ChevronDown' aria-label='Collapse Steps' />}</FluentLink>
                        :
                        ' '
                    }
                  </Stack.Item>
                  <Stack.Item> <div className="tre-notification-time">{getRelativeTime(props.operation.createdWhen)}</div></Stack.Item>
                </Stack>

                {
                  isExpanded &&
                  <>
                    <ul className="tre-notifications-steps-list">
                      {props.operation.steps && props.operation.steps.map((s: OperationStep, i: number) => {
                        return (
                          <li key={i}>
                            <Icon iconName={getIconAndColourForStatus(s.status)[0]} style={{ color: getIconAndColourForStatus(s.status)[1], position: 'relative', top: '2px', marginRight: '10px' }} />
                            {
                              s.stepId === "main" ?
                                <>{notification.resource.properties.display_name}: {props.operation.action}</> :
                                s.stepTitle
                            }
                          </li>)
                      })
                      }
                    </ul>
                  </>
                }
              </li>
      }
    </>);
};

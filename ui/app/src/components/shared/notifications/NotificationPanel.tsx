import { Callout, DirectionalHint, FontWeights, Link, mergeStyleSets, MessageBar, MessageBarType, Panel, Shimmer, ShimmerElementType, Text } from '@fluentui/react';
import React, { useContext, useEffect, useRef, useState } from 'react';
import { completedStates, inProgressStates, Operation } from '../../../models/operation';
import { NotificationsContext } from '../../../contexts/NotificationsContext';
import { NotificationItem } from './NotificationItem';
import { IconButton } from '@fluentui/react/lib/Button';
import { HttpMethod, useAuthApiCall } from '../../../useAuthApiCall';
import { ApiEndpoint } from '../../../models/apiEndpoints';
import { NotificationPoller } from './NotificationPoller';
import { TRENotification } from '../../../models/treNotification';
import { ComponentAction, getResourceFromResult, Resource } from '../../../models/resource';
import config from '../../../config.json';

export const NotificationPanel: React.FunctionComponent = () => {
  const opsContext = useContext(NotificationsContext);
  const opsWriteContext = useRef(useContext(NotificationsContext));
  const [isOpen, setIsOpen] = useState(false);
  const [showCallout, setShowCallout] = useState(false);
  const [loadingNotification, setLoadingNotification] = useState(false);
  const [notifications, setNotifications] = useState([] as Array<TRENotification>);
  const apiCall = useAuthApiCall();

  // NOTE: this first useEffect() hook will walk the tree of the TRE and add any running notifications to the panel on page load. 
  // It's very inefficient, and in future should be replaced by a single call to a new API Endpoint.
  // For now, it's behind a feature flag. To turn off, see the config.json - loadAllOpsOnStart
  useEffect(() => {
    const getOpsFromResourceList = async (resources: Array<Resource>, clientId?: string) => {

      let opsToAdd: Array<Operation> = [];
      const tasks: Array<any> = [];

      resources.forEach(async (r: Resource) => {
        tasks.push(apiCall(`${r.resourcePath}/${ApiEndpoint.Operations}`, HttpMethod.Get, clientId));
      });
      const results = await Promise.all(tasks);
      results.forEach((r: any) => {
        if (r && r.operations) {
          r.operations.forEach((o: Operation) => {
            if (inProgressStates.includes(o.status)) { opsToAdd.push(o) }
          });
        }
      });
      return opsToAdd;
    };

    const loadAllOps = async () => {
      console.warn("LOADING ALL OPERATIONS...");
      let opsToAdd: Array<Operation> = [];
      let workspaceList = (await apiCall(ApiEndpoint.Workspaces, HttpMethod.Get)).workspaces as Array<Resource>;
      workspaceList && workspaceList.length > 0 && (opsToAdd = opsToAdd.concat(await getOpsFromResourceList(workspaceList)));
      for (let i=0;i<workspaceList.length;i++){
        let w = workspaceList[i];
        let appId = w.properties.scope_id.replace("api://", "");
        let workspaceServicesList = (await apiCall(`${w.resourcePath}/${ApiEndpoint.WorkspaceServices}`, HttpMethod.Get, appId)).workspaceServices as Array<Resource>;
        if (workspaceServicesList && workspaceServicesList.length > 0) (opsToAdd = opsToAdd.concat(await getOpsFromResourceList(workspaceServicesList, appId)));
        for(let n=0;n<workspaceServicesList.length;n++){
          let ws = workspaceServicesList[n];
          let userResourcesList = (await apiCall(`${ws.resourcePath}/${ApiEndpoint.UserResources}`, HttpMethod.Get, appId)).userResources as Array<Resource>;
          if (userResourcesList && userResourcesList.length > 0) (opsToAdd = opsToAdd.concat(await getOpsFromResourceList(userResourcesList, appId)));
        }
      }
      opsWriteContext.current.addOperations(opsToAdd);
    };

    config.loadAllOpsOnStart && loadAllOps();
  }, [apiCall])

  useEffect(() => {
    const setupNotification = async (op: Operation) => {
      let workspaceAuth = false;
      let isWs = false;
      let ws = null;
      let resource = null;

      if (op.resourcePath.indexOf(ApiEndpoint.Workspaces) !== -1) {
        // we need the workspace to get auth details
        workspaceAuth = true;
        const wsId = op.resourcePath.split('/')[2];
        ws = (await apiCall(`${ApiEndpoint.Workspaces}/${wsId}`, HttpMethod.Get)).workspace;

        if (op.resourcePath.split('/').length === 3) {
          isWs = true;
          resource = ws;
        }

        if (!isWs) {
          let r = await apiCall(op.resourcePath, HttpMethod.Get, workspaceAuth ? ws.properties.scope_id.replace("api://", "") : null);
          resource = getResourceFromResult(r);
        }
      }

      return { operation: op, resource: resource, workspace: ws };
    }

    const syncOpsWithContext = async () => {
      opsContext.operations.forEach(async (ctxOp: Operation) => {
        if (notifications.findIndex((n: TRENotification) => ctxOp.id === n.operation.id) === -1) {
          setLoadingNotification(true);
          let currentNotifications = [...notifications];
          const n = await setupNotification(ctxOp);
          currentNotifications.splice(0, 0, n); // push the new notification to the beginning of the array
          setNotifications(currentNotifications);
          setLoadingNotification(false);
          opsContext.addResourceUpdate({
            resourceId: n.resource.id,
            operation: n.operation,
            componentAction: ComponentAction.Lock
          });
        }
      });
    };

    syncOpsWithContext();

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiCall, opsContext, opsContext.operations]); // the linter wants to include notifications in the deps, but we are choosing _not_ to re-trigger this hook on state change

  const updateNotification = (n: TRENotification) => {
    // splice the updated notification into the array
    let i = notifications.findIndex((v: TRENotification) => {
      return v.operation.id === n.operation.id;
    });
    let updatedNotifications = [...notifications];
    updatedNotifications.splice(i, 1, n);
    setNotifications(updatedNotifications);
    if (completedStates.includes(n.operation.status) && !isOpen) setShowCallout(true);

    // basic implementation for now, but this can be expanded to give more detailed info to subscribing components on operation changes
    opsContext.addResourceUpdate({
      resourceId: n.resource.id,
      operation: n.operation,
      componentAction: completedStates.includes(n.operation.status) ?
        (n.operation.status === "deleted" ? ComponentAction.Remove : ComponentAction.Reload) 
        : ComponentAction.Lock
    });
  }

  const dismissCompleted = () => {
    let inProgressNotifications = [] as Array<TRENotification>;
    notifications.forEach((n: TRENotification) => {
      if (!completedStates.includes(n.operation.status)) inProgressNotifications.push(n);
    });
    setNotifications(inProgressNotifications);
  }

  const styles = mergeStyleSets({
    buttonArea: {
      verticalAlign: 'top',
      display: 'inline-block',
      textAlign: 'center',
      margin: '0 100px',
      minWidth: 130,
      height: 32,
    },
    configArea: {
      width: 300,
      display: 'inline-block',
    },
    button: {
      width: 130,
    },
    callout: {
      width: 320,
      padding: '20px 24px',
    },
    title: {
      marginBottom: 12,
      fontWeight: FontWeights.semilight,
    },
    link: {
      display: 'block',
      marginTop: 20,
    },
  });

  // We had to separate out the polling logic from the notification item display as when the panel is collapsed the items are 
  // unmounted. We want to keep polling in the background, so NotificationPoller is a component without display, outside of the panel.
  return (
    <>
      <IconButton id="tre-notification-btn" className='tre-notifications-button' iconProps={{ iconName: notifications.length > 0 ? 'RingerSolid' : 'Ringer' }} onClick={() => setIsOpen(true)} title="Notifications" ariaLabel="Notifications" />
      {
        showCallout &&
        <Callout
          ariaLabelledBy={'labelId'}
          ariaDescribedBy={'descriptionId'}
          role="dialog"
          className={styles.callout}
          gapSpace={0}
          target={'#tre-notification-btn'}
          isBeakVisible={true}
          beakWidth={20}
          onDismiss={() => { setShowCallout(false) }}
          directionalHint={DirectionalHint.bottomLeftEdge}
          setInitialFocus
        >
          <Text block variant="xLarge" id={'labelId'}>
            Resource operation completed
          </Text>
          <br />
          <Text block variant="medium" id={'descriptionId'}>
            See notifications panel for detail
          </Text>
        </Callout>
      }
      {
        notifications.filter((v: TRENotification) => { return !completedStates.includes(v.operation.status) }).map((n: TRENotification, i: number) => {
          return (
            <NotificationPoller notification={n} updateNotification={(notification: TRENotification) => updateNotification(notification)} key={i} />
          )
        })
      }
      <Panel
        isLightDismiss
        headerText="Notifications"
        isOpen={isOpen}
        onDismiss={() => { setIsOpen(false) }}
        closeButtonAriaLabel="Close Notifications"
      >
        <div className="tre-notifications-dismiss">
          <Link href="#" onClick={(e) => { dismissCompleted(); return false; }} disabled={
            notifications.filter((f: TRENotification) => completedStates.includes(f.operation.status)).length === 0
          }>Dismiss Completed</Link>
        </div>
        {
          notifications.length === 0 && !loadingNotification &&
          <div style={{ marginTop: '20px' }}>
            <MessageBar
              messageBarType={MessageBarType.success}
              isMultiline={false}
            >
              No notifications to display
            </MessageBar>
          </div>
        }
        <ul className="tre-notifications-list">
          {
            loadingNotification &&
            <li>
              <Shimmer shimmerElements={[{ type: ShimmerElementType.gap, width: '100%' },]} />
              <Shimmer width="50%" />
              <Shimmer shimmerElements={[{ type: ShimmerElementType.gap, width: '100%' },]} />
              <Shimmer />
              <Shimmer shimmerElements={[{ type: ShimmerElementType.gap, width: '100%' },]} />
              <Shimmer />
            </li>
          }
          {
            notifications.map((n: TRENotification, i: number) => {
              return (
                <NotificationItem notification={n} key={i} />
              )
            })
          }
        </ul>
      </Panel>
    </>
  );
};

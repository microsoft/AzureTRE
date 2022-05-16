import { Panel } from '@fluentui/react';
import React, { useContext, useEffect, useState } from 'react';
import { Operation } from '../../../models/operation';
import { NotificationsContext } from './NotificationsContext';
import { NotificationItem } from './NotificationItem';
import { IconButton } from '@fluentui/react/lib/Button';
import { HttpMethod, useAuthApiCall } from '../../../useAuthApiCall';
import { ApiEndpoint } from '../../../models/apiEndpoints';
import { NotificationPoller } from './NotificationPoller';
import { TRENotification } from '../../../models/treNotification';

export const NotificationPanel: React.FunctionComponent = () => {
  const opsContext = useContext(NotificationsContext);
  const [isOpen, setIsOpen] = useState(true);
  const [notifications, setNotifications] = useState([] as Array<TRENotification>)

  const apiCall = useAuthApiCall();

  useEffect(() => {
    console.warn("ADDING NOTIFICATION");
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
          let r = await apiCall(op.resourcePath, HttpMethod.Get, workspaceAuth ? ws.properties.app_id : null);
          if (r['userResource']) resource = r.userResource;
          if (r['workspaceService']) resource = r.workspaceService;
          if (r['sharedService']) resource = r.sharedService;
        }
      }
  
      return {operation: op, resource: resource, workspace: ws };
    }

    const addOp = async () => {
      let currentNotifications = [...notifications];
      let n = await setupNotification(opsContext.latestOperation);
      currentNotifications.push(n);
      setNotifications(currentNotifications);
    };

    if(opsContext.latestOperation && opsContext.latestOperation.id) addOp();

  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiCall, opsContext.latestOperation]); // the linter wants to include notifications in the deps, but we are choosing _not_ to re-trigger this hook on state change

  const updateNotification = (n: TRENotification) => {
    console.log("Updated" , n);
    // splice the updated notification into the array
    let i = notifications.findIndex((v: TRENotification) => {
      return v.operation.createdWhen === n.operation.createdWhen; // TODO - change to Id
    });
    let updatedNotifications = [...notifications];
    updatedNotifications.splice(i, 1, n);
    console.log(updatedNotifications);
    setNotifications(updatedNotifications);
  }

  // We had to separate out the polling logic from the notification item display as when the panel is collapsed the items are 
  // unmounted. We want to keep polling in the background, so NotificationPoller is a component without display, above the panel.
  return (
    <>
      <IconButton className='tre-notifications-button' iconProps={{ iconName: 'Ringer' }} onClick={() => setIsOpen(true)} title="Notifications" ariaLabel="Notifications" />
      {
        notifications.map((n: TRENotification, i: number) => {
          return (
            <NotificationPoller notification={n} updateNotification={(notification: TRENotification) => updateNotification(notification)} key={i} />
          )
        })
      }
      <Panel
        headerText="Notifications"
        isOpen={isOpen}
        onDismiss={() => { setIsOpen(false) }}
        closeButtonAriaLabel="Close Notifications"
      >
        <ul className="tre-notifications-list">
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

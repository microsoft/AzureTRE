import { Panel, PrimaryButton } from '@fluentui/react';
import React, { useContext, useState } from 'react';
import { Operation } from '../../../models/operation';
import { NotificationsContext } from './NotificationsContext';
import dummyOp from './dummyOp.json';
import { NotificationItem } from './NotificationItem';
import { IconButton } from '@fluentui/react/lib/Button';

export const NotificationPanel: React.FunctionComponent = () => {
  const opsContext = useContext(NotificationsContext);
  const [isOpen, setIsOpen] = useState(true);

  const addSampleNotification = () => {
    console.log("adding test notification", (dummyOp as Operation).status);
    opsContext.addOperation(dummyOp as Operation);
  }

  return (
    <>
      <IconButton className='tre-notifications-button' iconProps={{ iconName: 'Ringer' }} onClick={() => setIsOpen(true)} title="Notifications" ariaLabel="Notifications" />
      <Panel
        headerText="Notifications"
        isOpen={isOpen}
        onDismiss={() => { setIsOpen(false) }}
        closeButtonAriaLabel="Close Notifications"
      >
        <ul className="tre-notifications-list">
          {
            opsContext.operations.map((op: Operation, i: number) => {
              return (
                <NotificationItem operation={op} key={i} />
              )
            })
          }
        </ul>
        <PrimaryButton onClick={() => addSampleNotification()}>Add Test Notification</PrimaryButton>
      </Panel>
    </>
  );
};

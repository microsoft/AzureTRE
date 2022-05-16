import { PrimaryButton } from '@fluentui/react';
import React, { useContext } from 'react';
import { Operation } from '../../../models/operation';
import { NotificationsContext } from './NotificationsContext';
import dummyOp from './dummyOp.json';
import { NotificationItem } from './NotificationItem';

export const NotificationPanel: React.FunctionComponent = () => {
  const opsContext = useContext(NotificationsContext);

  const addSampleNotification = () => {
    console.log("adding test notification", (dummyOp as Operation).status);
    opsContext.addOperation(dummyOp as Operation);
  }

  return (
      <div>
        <h1>Notifications</h1>
        <ul>
          {
            opsContext.operations.map((op: Operation, i:number) => {
              return (
                <NotificationItem operation={op} key={i}/>
              )
            })
          } 
        </ul>

        <PrimaryButton onClick={() => addSampleNotification()}>Add Test Notification</PrimaryButton>
      </div>
  );
};

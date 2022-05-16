import React, { useContext } from 'react';
import { Operation } from '../../../models/operation';
import { PrimaryButton } from '@fluentui/react';
import { NotificationsContext } from './NotificationsContext';
import dummyOp from './dummyOp.json';

export const AddNotificationDemo: React.FunctionComponent = () => {
  const opsContext = useContext(NotificationsContext);
  
  const addSampleNotification = () => {
    let d = JSON.parse(JSON.stringify(dummyOp)) as Operation; // avoid reusing the same object
    d.createdWhen = Math.random();
    console.log("adding test notification", d);
    opsContext.addOperation(d);
  }

  return (
    <PrimaryButton onClick={() => addSampleNotification()}>Add Test Notification</PrimaryButton>
  );
};

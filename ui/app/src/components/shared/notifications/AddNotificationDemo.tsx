import React, { useContext } from 'react';
import { Operation } from '../../../models/operation';
import { PrimaryButton } from '@fluentui/react';
import { NotificationsContext } from '../../../contexts/NotificationsContext';
import dummyOp from './dummyOp.json';
import dummyOpSteps from './dummyOpSteps.json';
import { HttpMethod, ResultType, useAuthApiCall } from '../../../useAuthApiCall';

export const AddNotificationDemo: React.FunctionComponent = () => {
  const opsContext = useContext(NotificationsContext);
  const apiCall = useAuthApiCall();

  const addSampleNotification = () => {
    let d = JSON.parse(JSON.stringify(dummyOp)) as Operation; // avoid reusing the same object
    console.log("adding test notification", d);
    opsContext.addOperation(d);
  }

  const addSampleNotificationWithSteps = () => {
    let d = JSON.parse(JSON.stringify(dummyOpSteps)) as Operation; // avoid reusing the same object
    console.log("adding test notification with steps", d);
    opsContext.addOperation(d);
  }

  const postDemoPatch = async () => {
    let body = {
      properties: {
        description: `Updated ${new Date().getTime()}`
      }
    }
    // patch "Jda VM"
    let op = await apiCall("workspaces/1e800001-7385-46a1-9f6d-490a6201ea01/workspace-services/8c70974a-5f66-4ae9-9502-7a54e9e0bb86/user-resources/8b6e42a0-e236-46ae-9541-01b462e4b468", HttpMethod.Patch, "816634e3-141d-4183-87a1-aaf2b95b7e12", body, ResultType.JSON, undefined, undefined, "*");
    opsContext.addOperation(op.operation);
  }

  const postMultiStageVm = async () => {
    let body = {
      templateName: "tre-service-dev-vm",
      properties: {
        display_name: "my user resource",
        description: "some description"
      }
    }
    let op = await apiCall("workspaces/30314a30-ddf5-4b66-9854-fa580c00b54e/workspace-services/6fba7e63-96bd-4253-aacb-76f62137fd63/user-resources", HttpMethod.Post, "653a0b60-b798-401d-a6cb-3e824b6f4308", body, ResultType.JSON, undefined, undefined, "*");
    opsContext.addOperation(op.operation);
  }

  return (
    <>
    <h4>Notifications test harness</h4>
      <PrimaryButton onClick={() => addSampleNotification()}>Add Test Notification</PrimaryButton>&nbsp;
      <PrimaryButton onClick={() => addSampleNotificationWithSteps()}>Add Test Notification (with steps)</PrimaryButton>&nbsp;
      <PrimaryButton onClick={() => postDemoPatch()}>Patch a real VM</PrimaryButton>&nbsp;
      <PrimaryButton onClick={() => postMultiStageVm()}>Post a multi-step VM</PrimaryButton>
    </>
  );
};

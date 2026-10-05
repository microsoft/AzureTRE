import React, { useEffect, useRef, useState } from "react";
import { DefaultButton, IButtonStyles, IconButton } from "@fluentui/react";
import { ComponentAction, Resource, VMPowerStates } from "../../models/resource";
import { ResourceType } from "../../models/resourceType";
import { actionsDisabledStates } from "../../models/operation";
import { TemplateAction } from "../../models/resourceTemplate";
import { useResourceTemplate } from "../../hooks/useResourceTemplate";
import { useInvokeResourceAction } from "../../hooks/useInvokeResourceAction";
import { SecuredByRole } from "./SecuredByRole";
import { ConfirmStopVM } from "./ConfirmStopVM";
import { APIError } from "../../models/exceptions";
import { ExceptionLayout } from "./ExceptionLayout";

interface VMPowerButtonProps {
  resource: Resource;
  componentAction: ComponentAction;
  className?: string;
  styles?: IButtonStyles;
  iconOnly?: boolean;
}

const findAction = (actions: Array<TemplateAction> | undefined, name: string) =>
  actions?.find((a) => a.name.toLowerCase() === name);

export const isVirtualMachineResource = (resource: Resource) =>
  resource.resourceType === ResourceType.UserResource && !!resource.azureStatus?.powerState;

// True when VMPowerButton renders for this resource, so Start/Stop shouldn't be duplicated elsewhere.
export const hasVMPowerControl = (resource: Resource, actions: Array<TemplateAction> | undefined) =>
  isVirtualMachineResource(resource) && !!findAction(actions, "start") && !!findAction(actions, "stop");

// Start/Stop for virtual machine user resources, shown when the template provides start and stop actions.
export const VMPowerButton: React.FunctionComponent<VMPowerButtonProps> = (props: VMPowerButtonProps) => {
  const isVM = isVirtualMachineResource(props.resource);
  const { resourceTemplate, roles } = useResourceTemplate(isVM ? props.resource : undefined);
  const invokeAction = useInvokeResourceAction();
  const [confirmStop, setConfirmStop] = useState(false);
  const [requested, setRequested] = useState(false);
  const [apiError, setApiError] = useState<APIError>();
  const [failedAction, setFailedAction] = useState<TemplateAction>();
  const powerState = props.resource.azureStatus?.powerState;

  // Allow another request once the power state or operation lock changes, and drop a Stop confirmation that no
  // longer matches the VM's state.
  useEffect(() => {
    setRequested(false);
    setConfirmStop(false);
  }, [powerState, props.componentAction]);

  // The button is reused when a detail route switches resource; reset state that belongs to the previous one.
  const resourceId = props.resource.id;
  const currentResourceId = useRef(resourceId);
  currentResourceId.current = resourceId;
  useEffect(() => {
    setConfirmStop(false);
    setRequested(false);
    setApiError(undefined);
    setFailedAction(undefined);
  }, [resourceId]);

  if (!hasVMPowerControl(props.resource, resourceTemplate.customActions)) return null;
  const startAction = findAction(resourceTemplate.customActions, "start") as TemplateAction;
  const stopAction = findAction(resourceTemplate.customActions, "stop") as TemplateAction;

  const isRunning = powerState === VMPowerStates.Running;
  const isStopped = powerState === VMPowerStates.Deallocated || powerState === VMPowerStates.Stopped;
  const inTransition = !isRunning && !isStopped;
  const disabled =
    requested ||
    inTransition ||
    props.componentAction === ComponentAction.Lock ||
    actionsDisabledStates.includes(props.resource.deploymentStatus) ||
    !props.resource.isEnabled;

  const run = async (action: TemplateAction) => {
    const invokedFor = props.resource.id;
    setRequested(true);
    setApiError(undefined);
    try {
      await invokeAction(props.resource, action.name);
      if (currentResourceId.current !== invokedFor) return;
      setFailedAction(undefined);
    } catch (e) {
      if (currentResourceId.current !== invokedFor) return;
      setRequested(false);
      const error = e as APIError;
      const verb = action.name.toLowerCase() === "stop" ? "stopping" : "starting";
      error.userMessage = error.userMessage || `Error ${verb} virtual machine`;
      setApiError(error);
      setFailedAction(action);
    }
  };

  const text = inTransition
    ? powerState === VMPowerStates.Starting
      ? "Starting"
      : "Stopping"
    : isRunning
      ? "Stop"
      : "Start";

  const title = disabled
    ? "VM must be enabled, deployed and not already changing state"
    : isRunning
      ? "Stop: power off the VM. You can start it again later."
      : "Start: power on the VM";
  const onClick = () => (isRunning ? setConfirmStop(true) : run(startAction));

  return (
    <SecuredByRole
      allowedWorkspaceRoles={roles}
      element={
        // Stop clicks (including those from the dialog portal) reaching a clickable parent card.
        <span onClick={(e) => e.stopPropagation()}>
          {props.iconOnly ? (
            <IconButton
              iconProps={{ iconName: isRunning ? "Stop" : "Play" }}
              ariaLabel={text}
              title={title}
              disabled={disabled}
              onClick={onClick}
            />
          ) : (
            <DefaultButton
              className={props.className}
              styles={props.styles}
              iconProps={{ iconName: isRunning ? "Stop" : "Play" }}
              text={text}
              disabled={disabled}
              title={title}
              onClick={onClick}
            />
          )}
          {confirmStop && (
            <ConfirmStopVM
              onDismiss={() => setConfirmStop(false)}
              onConfirm={() => {
                setConfirmStop(false);
                run(stopAction);
              }}
            />
          )}
          {apiError && failedAction && <ExceptionLayout e={apiError} onRetry={() => run(failedAction)} />}
        </span>
      }
    />
  );
};

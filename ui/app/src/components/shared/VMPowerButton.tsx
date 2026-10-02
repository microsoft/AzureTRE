import React, { useEffect, useState } from "react";
import { DefaultButton, IButtonStyles, IconButton } from "@fluentui/react";
import { ComponentAction, Resource, VMPowerStates } from "../../models/resource";
import { ResourceType } from "../../models/resourceType";
import { actionsDisabledStates } from "../../models/operation";
import { TemplateAction } from "../../models/resourceTemplate";
import { useResourceTemplate } from "../../hooks/useResourceTemplate";
import { useInvokeResourceAction } from "../../hooks/useInvokeResourceAction";
import { SecuredByRole } from "./SecuredByRole";
import { ConfirmStopVM } from "./ConfirmStopVM";

interface VMPowerButtonProps {
  resource: Resource;
  componentAction: ComponentAction;
  className?: string;
  styles?: IButtonStyles;
  iconOnly?: boolean;
}

const findAction = (actions: Array<TemplateAction> | undefined, name: string) =>
  actions?.find((a) => a.name.toLowerCase() === name);

// Start/Stop for virtual machine user resources, shown when the template provides start and stop actions.
export const VMPowerButton: React.FunctionComponent<VMPowerButtonProps> = (props: VMPowerButtonProps) => {
  const isVM = props.resource.resourceType === ResourceType.UserResource && !!props.resource.azureStatus?.powerState;
  const { resourceTemplate, roles } = useResourceTemplate(isVM ? props.resource : undefined);
  const invokeAction = useInvokeResourceAction();
  const [confirmStop, setConfirmStop] = useState(false);
  const [requested, setRequested] = useState(false);
  const powerState = props.resource.azureStatus?.powerState;

  // Allow another request once the power state or operation lock changes.
  useEffect(() => setRequested(false), [powerState, props.componentAction]);

  const startAction = findAction(resourceTemplate.customActions, "start");
  const stopAction = findAction(resourceTemplate.customActions, "stop");
  if (!isVM || !startAction || !stopAction) return null;

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
    setRequested(true);
    try {
      await invokeAction(props.resource, action.name);
    } catch (e) {
      setRequested(false);
      throw e;
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
        </span>
      }
    />
  );
};

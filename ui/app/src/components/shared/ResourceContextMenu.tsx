import React, { useContext, useState } from "react";
import { ComponentAction, VMPowerStates, Resource } from "../../models/resource";
import { CommandBar, IconButton, IContextualMenuItem, IContextualMenuProps } from "@fluentui/react";
import { SecuredByRole } from "./SecuredByRole";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { getActionDisplayName, getActionIcon, TemplateAction } from "../../models/resourceTemplate";
import { useResourceTemplate } from "../../hooks/useResourceTemplate";
import { useInvokeResourceAction } from "../../hooks/useInvokeResourceAction";
import { ConfirmStopVM } from "./ConfirmStopVM";
import { ConfirmDeleteResource } from "./ConfirmDeleteResource";
import { ConfirmCopyUrlToClipboard } from "./ConfirmCopyUrlToClipboard";
import { ConfirmDisableEnableResource } from "./ConfirmDisableEnableResource";
import { CreateUpdateResourceContext } from "../../contexts/CreateUpdateResourceContext";
import { actionsDisabledStates } from "../../models/operation";
import { ConfirmUpgradeResource } from "./ConfirmUpgradeResource";

interface ResourceContextMenuProps {
  resource: Resource;
  componentAction: ComponentAction;
  commandBar?: boolean;
  isExposedExternally?: boolean;
}

export const ResourceContextMenu: React.FunctionComponent<ResourceContextMenuProps> = (
  props: ResourceContextMenuProps,
) => {
  const workspaceCtx = useContext(WorkspaceContext);
  const [showDisable, setShowDisable] = useState(false);
  const [showDelete, setShowDelete] = useState(false);
  const [showCopyUrl, setShowCopyUrl] = useState(false);
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [stopActionName, setStopActionName] = useState("");
  const createFormCtx = useContext(CreateUpdateResourceContext);
  const { resourceTemplate, parentResource, roles } = useResourceTemplate(props.resource);
  const invokeAction = useInvokeResourceAction();

  const doAction = (actionName: string) => invokeAction(props.resource, actionName);

  // context menu
  let menuItems: Array<any> = [];

  menuItems = [
    {
      key: "update",
      text: "Update",
      iconProps: { iconName: "WindowEdit" },
      onClick: () =>
        createFormCtx.openCreateForm({
          resourceType: props.resource.resourceType,
          updateResource: props.resource,
          resourceParent: parentResource,
          workspaceApplicationIdURI: workspaceCtx.workspaceApplicationIdURI,
        }),
      disabled: props.componentAction === ComponentAction.Lock,
    },
    {
      key: "disable",
      text: props.resource.isEnabled ? "Disable" : "Enable",
      title: props.resource.isEnabled
        ? "Disable this resource in TRE. It must be disabled before it can be deleted."
        : "Enable this resource in TRE.",
      iconProps: {
        iconName: props.resource.isEnabled ? "CirclePause" : "PlayResume",
      },
      onClick: () => setShowDisable(true),
      disabled: props.componentAction === ComponentAction.Lock,
    },
    {
      key: "delete",
      text: "Delete",
      title: props.resource.isEnabled ? "Resource must be disabled before deleting" : "Delete this resource",
      iconProps: { iconName: "Delete" },
      onClick: () => setShowDelete(true),
      disabled: props.resource.isEnabled || props.componentAction === ComponentAction.Lock,
    },
  ];

  const shouldDisableConnect = () => {
    return (
      props.componentAction === ComponentAction.Lock ||
      actionsDisabledStates.includes(props.resource.deploymentStatus) ||
      !props.resource.isEnabled ||
      (props.resource.azureStatus?.powerState && props.resource.azureStatus.powerState !== VMPowerStates.Running)
    );
  };

  // add 'connect' button if we have a URL to connect to
  if (props.resource.properties.connection_uri && !props.commandBar) {
    const isExposedExternally = props.resource.properties.is_exposed_externally ?? props.isExposedExternally ?? true;
    if (isExposedExternally) {
      menuItems.push({
        key: "connect",
        text: "Connect",
        title: shouldDisableConnect()
          ? "Resource must be deployed, enabled & powered on to connect"
          : "Connect to resource",
        iconProps: { iconName: "PlugConnected" },
        onClick: () => {
          window.open(props.resource.properties.connection_uri, "_blank");
        },
        disabled: shouldDisableConnect(),
      });
    } else {
      menuItems.push({
        key: "connect",
        text: "Connect",
        title: shouldDisableConnect()
          ? "Resource must be deployed, enabled & powered on to connect"
          : "Connect to resource",
        iconProps: { iconName: "PlugConnected" },
        onClick: () => setShowCopyUrl(true),
        disabled: shouldDisableConnect(),
      });
    }
  }

  const shouldDisableActions = () => {
    return (
      props.componentAction === ComponentAction.Lock ||
      actionsDisabledStates.includes(props.resource.deploymentStatus) ||
      !props.resource.isEnabled
    );
  };

  // add custom actions if we have any
  if (resourceTemplate && resourceTemplate.customActions && resourceTemplate.customActions.length > 0) {
    let customActions: Array<IContextualMenuItem> = [];
    resourceTemplate.customActions.forEach((a: TemplateAction) => {
      customActions.push({
        key: a.name,
        text: getActionDisplayName(a.name),
        title: a.name.toLowerCase() === "stop" ? "Power off the VM. You can start it again later." : a.description,
        iconProps: { iconName: getActionIcon(a.name) },
        className: "tre-context-menu",
        onClick: () => {
          if (a.name.toLowerCase() === "stop") {
            setStopActionName(a.name);
          } else {
            doAction(a.name);
          }
        },
      });
    });
    menuItems.push({
      key: "custom-actions",
      text: "Actions",
      title: shouldDisableActions() ? "Resource must be deployed and enabled to perform actions" : "Custom Actions",
      iconProps: { iconName: "Asterisk" },
      disabled: shouldDisableActions(),
      subMenuProps: { items: customActions },
    });
  }

  // add 'upgrade' button if we have available template upgrades
  const nonMajorUpgrades = props.resource.availableUpgrades?.filter((upgrade) => !upgrade.forceUpdateRequired);
  if (nonMajorUpgrades?.length > 0) {
    menuItems.push({
      key: "upgrade",
      text: "Upgrade",
      title: "Upgrade this resource template version",
      iconProps: { iconName: "Refresh" },
      onClick: () => setShowUpgrade(true),
      disabled: props.componentAction === ComponentAction.Lock,
    });
  }

  const menuProps: IContextualMenuProps = {
    shouldFocusOnMount: true,
    items: menuItems,
  };

  return (
    <>
      <SecuredByRole
        allowedWorkspaceRoles={roles}
        allowedAppRoles={roles}
        element={
          props.commandBar ? (
            <CommandBar items={menuItems} ariaLabel="Resource actions" />
          ) : (
            <IconButton
              iconProps={{ iconName: "More" }}
              ariaLabel="More actions"
              title="More actions"
              menuProps={menuProps}
              className="tre-hide-chevron"
              disabled={props.componentAction === ComponentAction.Lock}
            />
          )
        }
      />
      {showDisable && (
        <ConfirmDisableEnableResource
          onDismiss={() => setShowDisable(false)}
          resource={props.resource}
          isEnabled={!props.resource.isEnabled}
        />
      )}
      {showDelete && <ConfirmDeleteResource onDismiss={() => setShowDelete(false)} resource={props.resource} />}
      {showCopyUrl && <ConfirmCopyUrlToClipboard onDismiss={() => setShowCopyUrl(false)} resource={props.resource} />}
      {showUpgrade && <ConfirmUpgradeResource onDismiss={() => setShowUpgrade(false)} resource={props.resource} />}
      {stopActionName && (
        <ConfirmStopVM
          onDismiss={() => setStopActionName("")}
          onConfirm={() => {
            const actionName = stopActionName;
            setStopActionName("");
            doAction(actionName);
          }}
        />
      )}
    </>
  );
};

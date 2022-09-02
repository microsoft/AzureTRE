import React, { useContext, useEffect, useRef, useState } from 'react';
import { ComponentAction, VMPowerStates, Resource } from '../../models/resource';
import { CommandBar, IconButton, IContextualMenuItem, IContextualMenuProps } from '@fluentui/react';
import { RoleName, WorkspaceRoleName } from '../../models/roleNames';
import { SecuredByRole } from './SecuredByRole';
import { ResourceType } from '../../models/resourceType';
import { OperationsContext } from '../../contexts/OperationsContext';
import { HttpMethod, useAuthApiCall } from '../../hooks/useAuthApiCall';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { UserResource } from '../../models/userResource';
import { getActionIcon, ResourceTemplate, TemplateAction } from '../../models/resourceTemplate';
import { ConfirmDeleteResource } from './ConfirmDeleteResource';
import { ConfirmDisableEnableResource } from './ConfirmDisableEnableResource';
import { CreateUpdateResourceContext } from '../../contexts/CreateUpdateResourceContext';
import { Workspace } from '../../models/workspace';
import { WorkspaceService } from '../../models/workspaceService';
import { actionsDisabledStates } from '../../models/operation';

interface ResourceContextMenuProps {
  resource: Resource,
  componentAction: ComponentAction,
  commandBar?: boolean
}

export const ResourceContextMenu: React.FunctionComponent<ResourceContextMenuProps> = (props: ResourceContextMenuProps) => {
  const apiCall = useAuthApiCall();
  const workspaceCtx = useContext(WorkspaceContext);
  const [showDisable, setShowDisable] = useState(false);
  const [showDelete, setShowDelete] = useState(false);
  const [resourceTemplate, setResourceTemplate] = useState({} as ResourceTemplate);
  const createFormCtx = useContext(CreateUpdateResourceContext);
  const opsWriteContext = useRef(useContext(OperationsContext)); // useRef to avoid re-running a hook on context write
  const [parentResource, setParentResource] = useState({} as WorkspaceService | Workspace);

  // get the resource template
  useEffect(() => {
    const getTemplate = async () => {
      if (!props.resource || !props.resource.id) return;
      let templatesPath;
      switch (props.resource.resourceType) {
        case ResourceType.Workspace:
          templatesPath = ApiEndpoint.WorkspaceTemplates; break;
        case ResourceType.WorkspaceService:
          templatesPath = ApiEndpoint.WorkspaceServiceTemplates; break;
        case ResourceType.SharedService:
          templatesPath = ApiEndpoint.SharedServiceTemplates; break;
        case ResourceType.UserResource:
          const ur = props.resource as UserResource;
          const parentService = (await apiCall(
            `${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.WorkspaceServices}/${ur.parentWorkspaceServiceId}`,
            HttpMethod.Get,
            workspaceCtx.workspaceApplicationIdURI))
            .workspaceService;
            setParentResource(parentService);
          templatesPath = `${ApiEndpoint.WorkspaceServiceTemplates}/${parentService.templateName}/${ApiEndpoint.UserResourceTemplates}`; break;
        default:
          throw Error('Unsupported resource type.');
      }
      const template = await apiCall(`${templatesPath}/${props.resource.templateName}`, HttpMethod.Get);
      setResourceTemplate(template);
    };
    getTemplate();
  }, [apiCall, props.resource, workspaceCtx.workspace.id, workspaceCtx.workspaceApplicationIdURI]);

  const doAction = async (actionName: string) => {
    const action = await apiCall(`${props.resource.resourcePath}/${ApiEndpoint.InvokeAction}?action=${actionName}`, HttpMethod.Post, workspaceCtx.workspaceApplicationIdURI);
    action && action.operation && opsWriteContext.current.addOperations([action.operation]);
  }

  // context menu
  let menuItems: Array<any> = [];
  let roles: Array<string> = [];
  let wsAuth = false;

  menuItems = [
    {
      key: 'update',
      text: 'Update',
      iconProps: { iconName: 'WindowEdit' },
      onClick: () => createFormCtx.openCreateForm({
        resourceType: props.resource.resourceType,
        updateResource: props.resource,
        resourceParent: parentResource,
        workspaceApplicationIdURI: workspaceCtx.workspaceApplicationIdURI,
      }),
      disabled: (props.componentAction === ComponentAction.Lock)
    },
    {
      key: 'disable',
      text: props.resource.isEnabled ? 'Disable' : 'Enable',
      iconProps: { iconName: props.resource.isEnabled ? 'CirclePause' : 'PlayResume' },
      onClick: () => setShowDisable(true),
      disabled: (props.componentAction === ComponentAction.Lock)
    },
    {
      key: 'delete',
      text: 'Delete',
      title: props.resource.isEnabled ? 'Resource must be disabled before deleting' : 'Delete this resource',
      iconProps: { iconName: 'Delete' },
      onClick: () => setShowDelete(true),
      disabled: (props.resource.isEnabled || props.componentAction === ComponentAction.Lock)
    },
  ];

  const shouldDisableConnect = () => {
    return props.componentAction === ComponentAction.Lock
      || actionsDisabledStates.includes(props.resource.deploymentStatus)
      || !props.resource.isEnabled
      || (props.resource.azureStatus?.powerState && props.resource.azureStatus.powerState !== VMPowerStates.Running);
  }

  // add 'connect' button if we have a URL to connect to
  if (props.resource.properties.connection_uri) {
    menuItems.push({
      key: 'connect',
      text: 'Connect',
      title: shouldDisableConnect() ? 'Resource must be deployed, enabled & powered on to connect' : 'Connect to resource',
      iconProps: { iconName: 'PlugConnected' },
      onClick: () => { window.open(props.resource.properties.connection_uri, '_blank') },
      disabled: shouldDisableConnect()
    })
  }

  const shouldDisableActions = () => {
    return props.componentAction === ComponentAction.Lock
      || actionsDisabledStates.includes(props.resource.deploymentStatus)
      || !props.resource.isEnabled;
  }

  // add custom actions if we have any
  if (resourceTemplate && resourceTemplate.customActions && resourceTemplate.customActions.length > 0) {
    let customActions: Array<IContextualMenuItem> = [];
    resourceTemplate.customActions.forEach((a: TemplateAction) => {
      customActions.push(
        {
          key: a.name,
          text: a.name,
          title: a.description,
          iconProps: { iconName: getActionIcon(a.name) },
          className: 'tre-context-menu',
          onClick: () => { doAction(a.name) }
        }
      );
    });
    menuItems.push({
      key: 'custom-actions',
      text: 'Actions',
      title: shouldDisableActions() ? 'Resource must be deployed and enabled to perform actions': 'Custom Actions',
      iconProps: { iconName: 'Asterisk' },
      disabled: shouldDisableActions(),
      subMenuProps: { items: customActions }
    });
  }

  switch (props.resource.resourceType) {
    case ResourceType.Workspace:
    case ResourceType.SharedService:
      roles = [RoleName.TREAdmin];
      break;
    case ResourceType.WorkspaceService:
    case ResourceType.UserResource:
      wsAuth = true;
      roles = [WorkspaceRoleName.WorkspaceOwner];
      break;
  }

  const menuProps: IContextualMenuProps = {
    shouldFocusOnMount: true,
    items: menuItems
  };

  return (
    <>
      <SecuredByRole allowedRoles={roles} workspaceAuth={wsAuth} element={
        props.commandBar ?
        <CommandBar
          items={menuItems}
          ariaLabel="Resource actions"
      />
        :
        <IconButton iconProps={{ iconName: 'More' }} menuProps={menuProps} className="tre-hide-chevron" disabled={props.componentAction === ComponentAction.Lock} />
      } />
      {
        showDisable &&
        <ConfirmDisableEnableResource onDismiss={() => setShowDisable(false)} resource={props.resource} isEnabled={!props.resource.isEnabled} />
      }
      {
        showDelete &&
        <ConfirmDeleteResource onDismiss={() => setShowDelete(false)} resource={props.resource} />
      }
    </>
  )
};

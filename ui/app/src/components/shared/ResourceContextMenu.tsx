import React, { useContext, useEffect, useState } from 'react';
import { ComponentAction, VMPowerStates, Resource } from '../../models/resource';
import { CommandBar, IconButton, IContextualMenuItem, IContextualMenuProps } from '@fluentui/react';
import { RoleName, WorkspaceRoleName } from '../../models/roleNames';
import { SecuredByRole } from './SecuredByRole';
import { ResourceType } from '../../models/resourceType';
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
import { AppRolesContext } from '../../contexts/AppRolesContext';
import { useAppDispatch } from '../../hooks/customReduxHooks';
import { addUpdateOperation } from '../shared/notifications/operationsSlice';

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
  const [parentResource, setParentResource] = useState({} as WorkspaceService | Workspace);
  const [roles, setRoles] = useState([] as Array<string>);
  const [wsAuth, setWsAuth] = useState(false);
  const appRoles = useContext(AppRolesContext); // the user is in these roles which apply across the app
  const dispatch = useAppDispatch();

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

      let r = [] as Array<string>;
      let wsAuth = false;
      switch (props.resource.resourceType) {
        case ResourceType.SharedService:
          r = [RoleName.TREAdmin, WorkspaceRoleName.WorkspaceOwner];
          break;
        case ResourceType.WorkspaceService:
          r = [WorkspaceRoleName.WorkspaceOwner]
          wsAuth = true;
          break;
        case ResourceType.UserResource:
          r = [WorkspaceRoleName.WorkspaceOwner, WorkspaceRoleName.WorkspaceResearcher, WorkspaceRoleName.AirlockManager];
          wsAuth = true;
          break;
        case ResourceType.Workspace:
          r = [RoleName.TREAdmin];
          break;
      }
      setWsAuth(wsAuth);
      setRoles(r);

      // should we bother getting the template? if the user isn't in the right role they won't see the menu at all.
      const userRoles = wsAuth ? workspaceCtx.roles : appRoles.roles;
      if (userRoles && r.filter(x => userRoles.includes(x)).length > 0) {
        const template = await apiCall(`${templatesPath}/${props.resource.templateName}`, HttpMethod.Get);
        setResourceTemplate(template);
      }
    };
    getTemplate();
  }, [apiCall, props.resource, workspaceCtx.workspace.id, workspaceCtx.workspaceApplicationIdURI, appRoles.roles, workspaceCtx.roles]);

  const doAction = async (actionName: string) => {
    const action = await apiCall(`${props.resource.resourcePath}/${ApiEndpoint.InvokeAction}?action=${actionName}`, HttpMethod.Post, workspaceCtx.workspaceApplicationIdURI);
    action && action.operation && dispatch(addUpdateOperation(action.operation));
  }

  // context menu
  let menuItems: Array<any> = [];

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

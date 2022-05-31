import React, { useContext, useEffect, useRef, useState } from 'react';
import { ComponentAction, Resource, ResourceUpdate } from '../../models/resource';
import { IconButton, IContextualMenuItem, IContextualMenuProps } from '@fluentui/react';
import { RoleName, WorkspaceRoleName } from '../../models/roleNames';
import { SecuredByRole } from './SecuredByRole';
import { ResourceType } from '../../models/resourceType';
import { NotificationsContext } from '../../contexts/NotificationsContext';
import { HttpMethod, useAuthApiCall } from '../../useAuthApiCall';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { UserResource } from '../../models/userResource';
import { getActionIcon, ResourceTemplate, TemplateAction } from '../../models/resourceTemplate';
import { ConfirmDeleteResource } from './ConfirmDeleteResource';
import { ConfirmDisableEnableResource } from './ConfirmDisableEnableResource';

interface ResourceContextMenuProps {
  resource: Resource
}

export const ResourceContextMenu: React.FunctionComponent<ResourceContextMenuProps> = (props: ResourceContextMenuProps) => {
  const apiCall = useAuthApiCall();
  const workspaceCtx = useContext(WorkspaceContext);
  const [showDisable, setShowDisable] = useState(false);
  const [showDelete, setShowDelete] = useState(false);
  const [componentAction, setComponentAction] = useState(ComponentAction.None);
  const [resourceTemplate, setResourceTemplate] = useState({} as ResourceTemplate);

  const opsReadContext = useContext(NotificationsContext);
  const opsWriteContext = useRef(useContext(NotificationsContext)); // useRef to avoid re-running a hook on context write

  // get the resource template
  useEffect(() => {
    const getTemplate = async () => {
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
            workspaceCtx.workspaceClientId))
            .workspaceService;
          templatesPath = `${ApiEndpoint.WorkspaceServiceTemplates}/${parentService.templateName}/${ApiEndpoint.UserResourceTemplates}`; break;
        default:
          throw Error('Unsupported resource type.');
      }
      const template = await apiCall(`${templatesPath}/${props.resource.templateName}`, HttpMethod.Get);
      setResourceTemplate(template);
    };
    getTemplate();
  }, [apiCall, props.resource, workspaceCtx.workspace.id, workspaceCtx.workspaceClientId]);

  // set the latest component action
  useEffect(() => {
    let updates = opsReadContext.resourceUpdates.filter((r: ResourceUpdate) => { return r.resourceId === props.resource.id });
    setComponentAction((updates && updates.length > 0) ?
      updates[updates.length - 1].componentAction :
      ComponentAction.None);
  }, [opsReadContext.resourceUpdates, props.resource.id])

  const doAction = async (actionName: string) => {
    const action = await apiCall(`${props.resource.resourcePath}/${ApiEndpoint.InvokeAction}?action=${actionName}`, HttpMethod.Post, workspaceCtx.workspaceClientId);
    action && action.operation && opsWriteContext.current.addOperations([action.operation]);
  }

  // context menu
  let menuItems: Array<IContextualMenuItem> = [];
  let roles: Array<string> = [];
  let wsAuth = false;

  menuItems = [
    { key: 'update', text: 'Update', iconProps: { iconName: 'WindowEdit' }, onClick: () => console.log('update') },
    { key: 'disable', text: props.resource.isEnabled ? 'Disable' : 'Enable', iconProps: { iconName: props.resource.isEnabled ? 'CirclePause' : 'PlayResume' }, onClick: () => setShowDisable(true) },
    { key: 'delete', text: 'Delete', title: props.resource.isEnabled ? 'Must be disabled to delete' : 'Delete this resource', iconProps: { iconName: 'Delete' }, onClick: () => setShowDelete(true), disabled: props.resource.isEnabled },
  ];

  // add custom actions if we have any
  if (resourceTemplate && resourceTemplate.customActions && resourceTemplate.customActions.length > 0) {
    let customActions: Array<IContextualMenuItem> = [];
    resourceTemplate.customActions.forEach((a: TemplateAction) => {
      customActions.push(
        { key: a.name, text: a.name, title: a.description, iconProps: { iconName: getActionIcon(a.name) }, className: 'tre-context-menu', onClick: () => { doAction(a.name) } }
      );
    });
    menuItems.push({ key: 'custom-actions', text: 'Actions', iconProps: { iconName: 'Asterisk' }, subMenuProps: { items: customActions } });
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
        <IconButton iconProps={{ iconName: 'More' }} menuProps={menuProps} className="tre-hide-chevron" disabled={componentAction === ComponentAction.Lock} />
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

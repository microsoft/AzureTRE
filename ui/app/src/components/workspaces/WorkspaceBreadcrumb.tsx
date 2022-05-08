import React from 'react';
import { Breadcrumb, IBreadcrumbItem } from '@fluentui/react';
import { useLocation, useNavigate } from 'react-router-dom';


export const WorkspaceBreadcrumb: React.FunctionComponent = () => {
  const path = useLocation().pathname;
  const navigate = useNavigate();

  let parts = path.split('/');
  let workspaceId = parts[2];
  let workspaceServiceId = parts[4] || '';
  let userResourceId = parts[6] || '';

  const _onBreadcrumbItemClicked = (ev?: React.MouseEvent<HTMLElement>, item?: IBreadcrumbItem): void => {
    item && navigate(item.key);
  } 

  const items: IBreadcrumbItem[] = [
    { text: 'Dashboard', key: '/', onClick: _onBreadcrumbItemClicked },
    { text: `(ws): ${workspaceId}`, key: `/workspaces/${workspaceId}`, onClick: _onBreadcrumbItemClicked },
  ]

  if (workspaceServiceId) items.push({ text: `(wss): ${workspaceServiceId}`, key: `/workspaces/${workspaceId}/workspace-services/${workspaceServiceId}`, onClick: _onBreadcrumbItemClicked });
  if (userResourceId) items.push({ text: `(ur): ${userResourceId}`, key: `/workspaces/${workspaceId}/workspace-services/${workspaceServiceId}/user-resources/${userResourceId}`, onClick: _onBreadcrumbItemClicked });

  return (
    <div className='tre-workspace-breadcrumb'>

      <Breadcrumb
        items={items}
        maxDisplayedItems={5}
        ariaLabel="Workspace breadcrumb"
        overflowAriaLabel="More..."
      />

    </div>
  );
};


import React from 'react';
import { Workspace } from '../../models/workspace';

import { ResourceCardList } from '../shared/ResourceCardList';
import { Resource } from '../../models/resource';
import { IconButton, IContextualMenuProps, PrimaryButton, Stack } from '@fluentui/react';
import { SecuredByRole } from '../shared/SecuredByRole';
import { RoleName } from '../../models/roleNames';
import { CreateUpdateResource } from '../shared/CreateUpdateResource/CreateUpdateResource';
import { ResourceType } from '../../models/resourceType';
import { useBoolean } from '@fluentui/react-hooks';

interface RootDashboardProps {
  selectWorkspace: (workspace: Workspace) => void,
  workspaces: Array<Workspace>
}

export const RootDashboard: React.FunctionComponent<RootDashboardProps> = (props: RootDashboardProps) => {

  const [createPanelOpen, { setTrue: createNew, setFalse: closeCreatePanel }] = useBoolean(false);

  // context menu only seen by admins
  const menuProps: IContextualMenuProps = {
    shouldFocusOnMount: true,
    
    // TODO - implement this menu when update / delete components are available
    items: [
      { key: 'update', text: 'Update', iconProps: {iconName: 'WindowEdit' }, onClick: () => console.log('update clicked') },
      { key: 'disable', text: 'Disable', iconProps: {iconName: 'StatusCircleBlock' }, onClick: () => console.log('disable clicked') },
      { key: 'delete', text: 'Delete', iconProps: {iconName: 'Delete' }, onClick: () => console.log('delete clicked') }
    ],
  };

  const workspaceContextMenu = <SecuredByRole allowedRoles={[RoleName.TREAdmin]} element={
    <IconButton iconProps={{ iconName: 'More' }} menuProps={menuProps} className="tre-hide-chevron"/>
  } />

  return (
    <>
      <Stack horizontal horizontalAlign="space-between" style={{ padding: 10 }}>
        <h1>Workspaces</h1>
        <PrimaryButton iconProps={{ iconName: 'Add' }} text="Create new" onClick={createNew}/>
        <CreateUpdateResource isOpen={createPanelOpen} onClose={closeCreatePanel} resourceType={ResourceType.Workspace}/>
      </Stack>
      <ResourceCardList
        resources={props.workspaces}
        selectResource={(r: Resource) => { props.selectWorkspace(r as Workspace) }}
        contextMenuElement={workspaceContextMenu} 
        emptyText="No workspaces to display. Create one to get started." />
    </>
  );
};

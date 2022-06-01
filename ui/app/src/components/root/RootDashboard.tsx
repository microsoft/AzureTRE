import React from 'react';
import { Workspace } from '../../models/workspace';

import { ResourceCardList } from '../shared/ResourceCardList';
import { Resource } from '../../models/resource';
import { PrimaryButton, Stack } from '@fluentui/react';
import { CreateUpdateResource } from '../shared/CreateUpdateResource/CreateUpdateResource';
import { ResourceType } from '../../models/resourceType';
import { useBoolean } from '@fluentui/react-hooks';

interface RootDashboardProps {
  selectWorkspace?: (workspace: Workspace) => void,
  workspaces: Array<Workspace>,
  updateWorkspace: (w: Workspace) => void,
  removeWorkspace: (w: Workspace) => void,
  addWorkspace: (w: Workspace) => void
}

export const RootDashboard: React.FunctionComponent<RootDashboardProps> = (props: RootDashboardProps) => {
  const [createPanelOpen, { setTrue: createNew, setFalse: closeCreatePanel }] = useBoolean(false);

  return (
    <>
      <Stack className="tre-panel">
        <Stack.Item>
          <Stack horizontal horizontalAlign="space-between">
            <Stack.Item><h1>Workspaces</h1></Stack.Item>
            <Stack.Item style={{ width: 200, textAlign: 'right' }}><PrimaryButton iconProps={{ iconName: 'Add' }} text="Create new" onClick={createNew} /></Stack.Item>

            <CreateUpdateResource
              isOpen={createPanelOpen}
              onClose={closeCreatePanel}
              resourceType={ResourceType.Workspace}
              onAddResource={(r: Resource) => props.addWorkspace(r as Workspace)}
            />
          </Stack>
        </Stack.Item>
        <Stack.Item>
          <ResourceCardList
            resources={props.workspaces}
            updateResource={(r: Resource) => props.updateWorkspace(r as Workspace)}
            removeResource={(r: Resource) => props.removeWorkspace(r as Workspace)}
            emptyText="No workspaces to display. Create one to get started." />
        </Stack.Item>
      </Stack>
    </>
  );
};

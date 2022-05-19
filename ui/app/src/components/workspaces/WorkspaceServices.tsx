import React from 'react';
import { Resource } from '../../models/resource';
import { Workspace } from '../../models/workspace';
import { WorkspaceService } from '../../models/workspaceService';
import { ResourceCardList } from '../shared/ResourceCardList';
import { useBoolean } from '@fluentui/react-hooks';
import { PrimaryButton, Stack } from '@fluentui/react';
import { CreateUpdateResource } from '../shared/CreateUpdateResource/CreateUpdateResource';
import { ResourceType } from '../../models/resourceType';

interface WorkspaceServicesProps {
  workspace: Workspace,
  workspaceServices: Array<WorkspaceService>,
  setWorkspaceService: (workspaceService: WorkspaceService) => void
}

export const WorkspaceServices: React.FunctionComponent<WorkspaceServicesProps> = (props: WorkspaceServicesProps) => {

  const [createPanelOpen, { setTrue: createNew, setFalse: closeCreatePanel }] = useBoolean(false);

  return (
    <>
      <Stack horizontal horizontalAlign="space-between" style={{ padding: 10 }}>
        <h1>Workspace Services</h1>
        <PrimaryButton iconProps={{ iconName: 'Add' }} text="Create new" onClick={createNew}/>
        <CreateUpdateResource 
          isOpen={createPanelOpen}
          onClose={closeCreatePanel}
          resourceType={ResourceType.WorkspaceService}
          parentResource={props.workspace}
        />
      </Stack>
      <ResourceCardList
        resources={props.workspaceServices}
        selectResource={(r: Resource) => props.setWorkspaceService(r as WorkspaceService)}
        emptyText="This workspace has no workspace services." />
    </>
  );
};

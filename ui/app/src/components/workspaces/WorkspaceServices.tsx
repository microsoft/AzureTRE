import React from 'react';
import { Resource } from '../../models/resource';
import { Workspace } from '../../models/workspace';
import { WorkspaceService } from '../../models/workspaceService';
import { ResourceCardList } from '../shared/ResourceCardList';

interface WorkspaceServicesProps {
  workspace: Workspace,
  workspaceServices: Array<WorkspaceService>,
  setWorkspaceService: (workspaceService: WorkspaceService) => void
}

export const WorkspaceServices: React.FunctionComponent<WorkspaceServicesProps> = (props: WorkspaceServicesProps) => {

  return (
    <>
      <h1>Workspace Services</h1>
      <ResourceCardList
        resources={props.workspaceServices}
        selectResource={(r: Resource) => props.setWorkspaceService(r as WorkspaceService)}
        emptyText="This workspace has no workspace services." />
    </>
  );
};

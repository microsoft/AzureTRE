import React, { useContext } from 'react';
import { Resource } from '../../models/resource';
import { WorkspaceService } from '../../models/workspaceService';
import { ResourceCardList } from '../shared/ResourceCardList';
import { PrimaryButton, Stack } from '@fluentui/react';
import { ResourceType } from '../../models/resourceType';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import { CreateUpdateResourceContext } from '../../contexts/CreateUpdateResourceContext';
import { successStates } from '../../models/operation';
import { WorkspaceRoleName } from '../../models/roleNames';
import { SecuredByRole } from '../shared/SecuredByRole';

interface WorkspaceServicesProps {
  workspaceServices: Array<WorkspaceService>,
  setWorkspaceService: (workspaceService: WorkspaceService) => void,
  addWorkspaceService: (workspaceService: WorkspaceService) => void,
  updateWorkspaceService: (workspaceService: WorkspaceService) => void,
  removeWorkspaceService: (workspaceService: WorkspaceService) => void
}

export const WorkspaceServices: React.FunctionComponent<WorkspaceServicesProps> = (props: WorkspaceServicesProps) => {
  const workspaceCtx = useContext(WorkspaceContext);
  const createFormCtx = useContext(CreateUpdateResourceContext);

  return (
    <>
      <Stack className="tre-panel">
        <Stack.Item>
          <Stack horizontal horizontalAlign="space-between">
            <h1>Workspace Services</h1>
            <SecuredByRole allowedRoles={[WorkspaceRoleName.WorkspaceOwner]} workspaceAuth={true} element={
              <PrimaryButton iconProps={{ iconName: 'Add' }} text="Create new" disabled={successStates.indexOf(workspaceCtx.workspace.deploymentStatus) === -1 || !workspaceCtx.workspace.isEnabled} onClick={() => {
                createFormCtx.openCreateForm({
                  resourceType: ResourceType.WorkspaceService,
                  resourceParent: workspaceCtx.workspace,
                  onAdd: (r: Resource) => props.addWorkspaceService(r as WorkspaceService),
                  workspaceApplicationIdURI: workspaceCtx.workspaceApplicationIdURI
                });
              }} />
            } />
          </Stack>
        </Stack.Item>
        <Stack.Item>
          <ResourceCardList
            resources={props.workspaceServices}
            selectResource={(r: Resource) => props.setWorkspaceService(r as WorkspaceService)}
            updateResource={(r: Resource) => props.updateWorkspaceService(r as WorkspaceService)}
            removeResource={(r: Resource) => props.removeWorkspaceService(r as WorkspaceService)}
            emptyText="This workspace has no workspace services." />
        </Stack.Item>
      </Stack>
    </>
  );
};

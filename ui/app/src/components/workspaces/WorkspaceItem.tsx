import { Pivot, PivotItem, PrimaryButton } from '@fluentui/react';
import React, { useContext } from 'react';
import { WorkspaceRoleName } from '../../models/roleNames';
import { Workspace } from '../../models/workspace';
import { SecuredByRole } from '../shared/SecuredByRole';
import { ResourceDebug } from '../shared/ResourceDebug';
import { WorkspaceRolesContext } from './WorkspaceRolesContext';
import { WorkspaceOperationsPanel } from './WorkspaceOperationsPanel';

// TODO:
// - commands for managing workspace
// - nicer display of key properties

interface WorkspaceItemProps {
  workspace: Workspace
}

export const WorkspaceItem: React.FunctionComponent<WorkspaceItemProps> = (props: WorkspaceItemProps) => {
  const workspaceRoles = useContext(WorkspaceRolesContext);

  return (
    <>
      <Pivot aria-label="Basic Pivot Example">
        <PivotItem
          headerText="Overview"
          headerButtonProps={{
            'data-order': 1,
            'data-title': 'Overview',
          }}
        >
          <h3>--Workspace details panel here--</h3>

          <h3>Roles:</h3>
          <ul>
            {
              workspaceRoles.roles &&
              workspaceRoles.roles.map((role: string, i: number) => {
                return (
                  <li key={i}>{role}</li>
                )
              })
            }
          </ul>
          <SecuredByRole allowedRoles={[WorkspaceRoleName.WorkspaceOwner]} workspaceAuth={true} element={
            <PrimaryButton>Seen by workspace *owners* only</PrimaryButton>
          } />
          <ResourceDebug resource={props.workspace} />

        </PivotItem>
        <PivotItem headerText="History">
          <h3>--History goes here--</h3>


        </PivotItem>
        <PivotItem headerText="Operations">
            <WorkspaceOperationsPanel workspace={props.workspace} />
        </PivotItem>
      </Pivot>





    </>
  );
};

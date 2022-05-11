import { PrimaryButton } from '@fluentui/react';
import React, { useContext } from 'react';
import { WorkspaceRoleName } from '../../models/roleNames';
import { Workspace } from '../../models/workspace';
import { SecuredByRole } from '../shared/SecuredByRole';
import { ResourceDebug } from '../shared/ResourceDebug';
import { WorkspaceRolesContext } from './WorkspaceRolesContext';

// TODO:
// - commands for managing workspace
// - nicer display of key properties

interface WorkspaceItemProps {
  workspace: Workspace
}

export const WorkspaceItem: React.FunctionComponent<WorkspaceItemProps> = (props:WorkspaceItemProps) => {
  const workspaceRoles = useContext(WorkspaceRolesContext);

  return (
    <>
      <h3>Roles:</h3>
      <ul>
        {
          workspaceRoles.roles &&
          workspaceRoles.roles.map((role: String, i: number) => {
            return (
              <li key={i}>{role}</li>
            )
          })
        }
      </ul>


      <SecuredByRole allowedRoles={[WorkspaceRoleName.WorkspaceOwner]} workspaceAuth={true} element={
        <PrimaryButton>Seen by workspace *owners* only</PrimaryButton>
      } />

      &nbsp; 

      <SecuredByRole allowedRoles={[WorkspaceRoleName.WorkspaceResearcher]} workspaceAuth={true} element={
        <PrimaryButton>Seen by workspace *reseachers* only</PrimaryButton>
      } />

      &nbsp; 

      <SecuredByRole allowedRoles={[WorkspaceRoleName.WorkspaceOwner, WorkspaceRoleName.WorkspaceResearcher]} workspaceAuth={true} element={
        <PrimaryButton>Seen by workspace *owners* AND *reseachers*</PrimaryButton>
      } />
      
      <ResourceDebug resource={props.workspace} />
    </>
  );
};

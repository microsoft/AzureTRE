import React, { useContext } from 'react';
import { Link } from 'react-router-dom';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { Workspace } from '../../models/workspace';

import { RootRolesContext } from '../shared/RootRolesContext';
import { PrimaryButton, Stack } from '@fluentui/react';
import { SecuredByRole } from '../shared/SecuredByRole';
import { RoleName } from '../../models/roleNames';
import { CreateUpdateResource } from '../shared/CreateUpdateResource/CreateUpdateResource';
import { ResourceType } from '../../models/resourceType';

// TODO:
// - Create WorkspaceCard component + use instead of <Link>

interface RootDashboardProps {
  selectWorkspace: (workspace: Workspace) => void,
  workspaces: Array<Workspace>
}

export const RootDashboard: React.FunctionComponent<RootDashboardProps> = (props:RootDashboardProps) => {
  const rootRolesContext = useContext(RootRolesContext);

  return (
    <>
      <h3>TRE Roles</h3>
      <ul>
        {
          rootRolesContext.roles &&
          rootRolesContext.roles.map((role:string, i:number) => {
            return (
              <li key={i}>
                {role}
              </li>
            )
          })
        }
      </ul>
      <SecuredByRole allowedRoles={[RoleName.TREAdmin]} element={
        <PrimaryButton>Admin Only</PrimaryButton>
      } />
      &nbsp; 
      <SecuredByRole allowedRoles={[RoleName.TREAdmin, RoleName.TREUser]} element={
        <PrimaryButton>Admin + TRE User Only</PrimaryButton>
      } />
      &nbsp; 
      <SecuredByRole allowedRoles={["NotARole"]} element={
        <PrimaryButton>Will be hidden for all</PrimaryButton>
      } />
      <hr/>

      <Stack horizontal horizontalAlign="space-between">
        <h1>Workspaces</h1>
        <CreateUpdateResource resourceType={ResourceType.Workspace}></CreateUpdateResource>
      </Stack>

      <ul>
      {
        props.workspaces.map((ws, i) => {
          return (
            <li key={i}>
              <Link to={`/${ApiEndpoint.Workspaces}/${ws.id}`} onClick={() => props.selectWorkspace(ws)}>{ws.properties?.display_name}</Link>
            </li>
          )
        })
      }
      </ul>
    </>
  );
};

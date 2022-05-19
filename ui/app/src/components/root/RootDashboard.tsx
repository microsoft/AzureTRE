import React, { useContext } from 'react';
import { Link } from 'react-router-dom';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { Workspace } from '../../models/workspace';
import { useBoolean } from '@fluentui/react-hooks';
import { RootRolesContext } from '../shared/RootRolesContext';
import { PrimaryButton, Stack } from '@fluentui/react';
import { SecuredByRole } from '../shared/SecuredByRole';
import { RoleName } from '../../models/roleNames';
import { CreateUpdateResource } from '../shared/CreateUpdateResource/CreateUpdateResource';
import { ResourceType } from '../../models/resourceType';
import { AddNotificationDemo } from '../shared/notifications/AddNotificationDemo';

// TODO:
// - Create WorkspaceCard component + use instead of <Link>

interface RootDashboardProps {
  selectWorkspace: (workspace: Workspace) => void,
  workspaces: Array<Workspace>
}

export const RootDashboard: React.FunctionComponent<RootDashboardProps> = (props:RootDashboardProps) => {
  const rootRolesContext = useContext(RootRolesContext);
  const [createPanelOpen, { setTrue: createNew, setFalse: closeCreatePanel }] = useBoolean(false);

  return (
    <>
      <AddNotificationDemo />
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

      <Stack horizontal horizontalAlign="space-between" style={{ padding: 10 }}>
        <h1>Workspaces</h1>
        <PrimaryButton iconProps={{ iconName: 'Add' }} text="Create new" onClick={createNew}/>
        <CreateUpdateResource isOpen={createPanelOpen} onClose={closeCreatePanel} resourceType={ResourceType.Workspace}/>
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

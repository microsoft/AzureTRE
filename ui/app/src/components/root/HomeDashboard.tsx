import React, { useContext, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { Workspace } from '../../models/workspace';
import { HttpMethod, ResultType, useAuthApiCall } from '../../useAuthApiCall';

import config from '../../config.json';
import { RootRolesContext } from '../shared/RootRolesContext';
import { PrimaryButton } from '@fluentui/react';
import { SecuredByRole } from '../shared/SecuredByRole';
import { RoleName } from '../../models/roleNames';

// TODO:
// - Create WorkspaceCard component + use instead of <Link>
// - Spinner / placeholders for loading
// - Error handling for bad requests

interface HomeDashboardProps {
  selectWorkspace: (workspace: Workspace) => void
}

export const HomeDashboard: React.FunctionComponent<HomeDashboardProps> = (props:HomeDashboardProps) => {
  const [workspaces, setWorkspaces] = useState([{} as Workspace]);
  const rootRolesContext = useContext(RootRolesContext);
  const apiCall = useAuthApiCall();

  useEffect(() => {
    const getWorkspaces = async () => {
      const r = await apiCall(ApiEndpoint.Workspaces, HttpMethod.Get, undefined, undefined, ResultType.JSON, (roles: Array<String>) => {
        config.debug && console.log("Root Roles", roles);
        rootRolesContext.roles = roles;
      });

      setWorkspaces(r.workspaces);
    };
    getWorkspaces();
  }, [apiCall, rootRolesContext]);

  return (
    <>
      <h3>TRE Roles</h3>
      <ul>
        {
          rootRolesContext.roles.map((role:String, i:number) => {
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
      <h1>Workspaces</h1>
      <ul>
      {
        workspaces.map((ws, i) => {
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

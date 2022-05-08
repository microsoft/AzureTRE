import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { Workspace } from '../../models/workspace';
import { HttpMethod, useAuthApiCall } from '../../useAuthApiCall';

// TODO:
// - Create WorkspaceCard component + use instead of <Link>
// - Spinner / placeholders for loading
// - Error handling for bad requests

interface HomeDashboardProps {
  selectWorkspace: (workspace: Workspace) => void
}

export const HomeDashboard: React.FunctionComponent<HomeDashboardProps> = (props:HomeDashboardProps) => {
  const [workspaces, setWorkspaces] = useState([{} as Workspace]);
  const apiCall = useAuthApiCall();

  useEffect(() => {
    const getWorkspaces = async () => {
      const r = await apiCall(ApiEndpoint.Workspaces, HttpMethod.Get)
      setWorkspaces(r.workspaces);
    };
    getWorkspaces();
  }, [apiCall]);

  return (
    <>
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

import React from 'react';
import { Link } from 'react-router-dom';
import { Workspace } from '../../models/workspace';
import { WorkspaceService } from '../../models/workspaceService';

// TODO:
// - workspace service cards

interface WorkspaceServicesProps {
  workspace: Workspace,
  workspaceServices: Array<WorkspaceService>,
  setWorkspaceService: (workspaceService: WorkspaceService) => void
}

export const WorkspaceServices: React.FunctionComponent<WorkspaceServicesProps> = (props:WorkspaceServicesProps) => {

  return (
    <>
     <h1>Workspace Services Landing</h1>

      <h2>Services</h2>
      <ul>
      {
        props.workspaceServices.map((ws:WorkspaceService, i:number) => {
          return (
            <li key={i}><Link to={ws.id.toString()} onClick={() => props.setWorkspaceService(ws)}>{ws.properties.display_name}</Link></li>
          )
        })
      }
      </ul>
    </>
  );
};

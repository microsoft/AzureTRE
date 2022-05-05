import React, {  } from 'react';
import { useParams } from 'react-router-dom';
import { Workspace } from '../../models/workspace';

interface WorkspaceItemProps {
  workspace: Workspace
}

export const WorkspaceItem: React.FunctionComponent<WorkspaceItemProps> = (props:WorkspaceItemProps) => {
  const { workspaceId } = useParams();

  return (
    <>
      <h1>Workspace {workspaceId}</h1>
      <h2>Details:</h2>
      <ul>      
      {
        Object.keys(props.workspace).map((key, i) => {
          let val = typeof((props.workspace as any)[key]) === 'object' ?
            JSON.stringify((props.workspace as any)[key]) :
            (props.workspace as any)[key].toString()

          return (
            <li key={i}>
              <b>{key}: </b>{val}
            </li>
          )
        })
      }
      </ul>
    </>
  );
};

import React, {  } from 'react';
import { Workspace } from '../../models/workspace';
import { ResourceDebug } from './ResourceDebug';

// TODO:
// - commands for managing workspace
// - nicer display of key properties

interface WorkspaceItemProps {
  workspace: Workspace
}

export const WorkspaceItem: React.FunctionComponent<WorkspaceItemProps> = (props:WorkspaceItemProps) => {

  return (
    <>
      <ResourceDebug resource={props.workspace} />
    </>
  );
};

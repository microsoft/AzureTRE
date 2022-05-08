import React, {  } from 'react';
import { Workspace } from '../../models/workspace';
import { ResourceDebug } from './ResourceDebug';

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

import React from 'react';
import { Workspace } from '../../models/workspace';

import { ResourceCardList } from '../shared/ResourceCardList';
import { Resource } from '../../models/resource';

interface RootDashboardProps {
  selectWorkspace: (workspace: Workspace) => void,
  workspaces: Array<Workspace>
}

export const RootDashboard: React.FunctionComponent<RootDashboardProps> = (props: RootDashboardProps) => {

  return (
    <>
      <h1>Workspaces</h1>
      <ResourceCardList 
        resources={props.workspaces} 
        selectResource={(r: Resource) => {props.selectWorkspace(r as Workspace)}} 
        emptyText="No workspaces to display. Create one to get started." />
    </>
  );
};

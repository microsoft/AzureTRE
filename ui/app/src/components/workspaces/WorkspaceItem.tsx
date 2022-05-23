import { Pivot, PivotItem } from '@fluentui/react';
import React from 'react';
import { Workspace } from '../../models/workspace';
import { ResourceDebug } from '../shared/ResourceDebug';
import { ResourceHistory } from '../shared/ResourceHistory';
import { ResourcePropertyPanel } from '../shared/ResourcePropertyPanel';

interface WorkspaceItemProps {
  workspace: Workspace
}

export const WorkspaceItem: React.FunctionComponent<WorkspaceItemProps> = (props: WorkspaceItemProps) => {

  return (
    <>
      <Pivot aria-label="Basic Pivot Example">
        <PivotItem
          headerText="Overview"
          headerButtonProps={{
            'data-order': 1,
            'data-title': 'Overview',
          }}
        >

          <ResourcePropertyPanel resource={props.workspace} />
          <ResourceDebug resource={props.workspace} />

        </PivotItem>
        <PivotItem headerText="History">
          <ResourceHistory history={props.workspace.history} />
        </PivotItem>
        <PivotItem headerText="Operations">
          <h3>--Operations Log here</h3>
        </PivotItem>
      </Pivot>
    </>
  );
};

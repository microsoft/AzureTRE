import { Pivot, PivotItem } from '@fluentui/react';
import React from 'react';
import { Workspace } from '../../models/workspace';
import { ResourceDebug } from '../shared/ResourceDebug';
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
          <h3>--History goes here--</h3>
        </PivotItem>
        <PivotItem headerText="Operations">
          <h3>--Operations Log here</h3>
        </PivotItem>
      </Pivot>
    </>
  );
};

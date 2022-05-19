import { Pivot, PivotItem, PrimaryButton } from '@fluentui/react';
import React, { useContext } from 'react';
import { WorkspaceRoleName } from '../../models/roleNames';
import { Workspace } from '../../models/workspace';
import { SecuredByRole } from '../shared/SecuredByRole';
import { ResourceDebug } from '../shared/ResourceDebug';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import { ResourcePropertyPanel } from '../shared/ResourcePropertyPanel';

// TODO:
// - commands for managing workspace
// - nicer display of key properties

interface WorkspaceItemProps {
  workspace: Workspace
}

export const WorkspaceItem: React.FunctionComponent<WorkspaceItemProps> = (props: WorkspaceItemProps) => {
  const workspaceCtx = useContext(WorkspaceContext);

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

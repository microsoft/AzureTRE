import { Pivot, PivotItem } from '@fluentui/react';
import React, { useContext } from 'react';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import { ResourceDebug } from '../shared/ResourceDebug';
import { ResourceHistory } from '../shared/ResourceHistory';
import { ResourcePropertyPanel } from '../shared/ResourcePropertyPanel';

export const WorkspaceItem: React.FunctionComponent = () => {
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
          <ResourcePropertyPanel resource={workspaceCtx.workspace} />
          <ResourceDebug resource={workspaceCtx.workspace} />
        </PivotItem>
        <PivotItem headerText="History">
          <ResourceHistory history={workspaceCtx.workspace.history} />
        </PivotItem>
        <PivotItem headerText="Operations">
            <ResourceOperationsList resource={props.workspace} />
        </PivotItem>
      </Pivot>
    </>
  );
};

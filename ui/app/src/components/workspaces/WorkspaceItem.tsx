import { Pivot, PivotItem, Stack } from '@fluentui/react';
import React, { useContext } from 'react';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import { ResourceContextMenu } from '../shared/ResourceContextMenu';
import { ResourceDebug } from '../shared/ResourceDebug';
import { ResourceHistory } from '../shared/ResourceHistory';
import { ResourcePropertyPanel } from '../shared/ResourcePropertyPanel';
import { ResourceOperationsList } from './ResourceOperationsList';


export const WorkspaceItem: React.FunctionComponent = () => {
  const workspaceCtx = useContext(WorkspaceContext);

  return (
    <>
      <Stack horizontal>
        <Stack.Item grow={1}>
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
            <PivotItem headerText="History" >
              <ResourceHistory history={workspaceCtx.workspace.history} />
            </PivotItem>
            <PivotItem headerText="Operations">
            <ResourceOperationsList resource={workspaceCtx.workspace} />
            </PivotItem>
          </Pivot>
        </Stack.Item>
        <Stack.Item>
          <ResourceContextMenu resource={workspaceCtx.workspace} />
        </Stack.Item>
      </Stack>
    </>
  );
};

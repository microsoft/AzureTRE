import { Pivot, PivotItem } from '@fluentui/react';
import React, { useContext, useRef } from 'react';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import { Resource } from '../../models/resource';
import { Workspace } from '../../models/workspace';
import { useComponentManager } from '../../hooks/useComponentManager';
import { ResourceDebug } from '../shared/ResourceDebug';
import { ResourceHeader } from '../shared/ResourceHeader';
import { ResourceHistory } from '../shared/ResourceHistory';
import { ResourcePropertyPanel } from '../shared/ResourcePropertyPanel';
import { ResourceOperationsList } from '../shared/ResourceOperationsList';


export const WorkspaceItem: React.FunctionComponent = () => {
  const workspaceCtx = useRef(useContext(WorkspaceContext));
  const componentAction = useComponentManager(workspaceCtx.current.workspace, (r: Resource) => workspaceCtx.current.setWorkspace(r as Workspace));

  return (
    <>
      <ResourceHeader resource={workspaceCtx.current.workspace} componentAction={componentAction}/>
      <Pivot aria-label="Basic Pivot Example" className='tre-panel'>
        <PivotItem
          headerText="Overview"
          headerButtonProps={{
            'data-order': 1,
            'data-title': 'Overview',
          }}
        >
          <ResourcePropertyPanel resource={workspaceCtx.current.workspace} />
          <ResourceDebug resource={workspaceCtx.current.workspace} />
        </PivotItem>
        <PivotItem headerText="History" >
          <ResourceHistory history={workspaceCtx.current.workspace.history} />
        </PivotItem>
        <PivotItem headerText="Operations">
          <ResourceOperationsList resource={workspaceCtx.current.workspace} />
        </PivotItem>
      </Pivot>
    </>
  );
};

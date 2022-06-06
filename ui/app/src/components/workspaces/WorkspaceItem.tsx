import { Pivot, PivotItem } from '@fluentui/react';
import React, { useContext } from 'react';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import { Resource } from '../../models/resource';
import { Workspace } from '../../models/workspace';
import { useComponentManager } from '../../hooks/useComponentManager';
import { ResourceDebug } from '../shared/ResourceDebug';
import { ResourceHeader } from '../shared/ResourceHeader';
import { ResourceHistory } from '../shared/ResourceHistory';
import { ResourcePropertyPanel } from '../shared/ResourcePropertyPanel';
import { ResourceOperationsList } from '../shared/ResourceOperationsList';
import { useNavigate } from 'react-router-dom';


export const WorkspaceItem: React.FunctionComponent = () => {
  const workspaceCtx = useContext(WorkspaceContext);
  const navigate = useNavigate();

  const latestUpdate = useComponentManager(
    workspaceCtx.workspace,
    (r: Resource) => workspaceCtx.setWorkspace(r as Workspace),
    (r: Resource) => navigate(`/`)
  );

  return (
    <>
      <ResourceHeader resource={workspaceCtx.workspace} latestUpdate={latestUpdate}/>
      <Pivot aria-label="Workspace Information" className='tre-panel'>
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
    </>
  );
};

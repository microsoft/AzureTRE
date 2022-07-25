import React, { } from 'react';
import { ResourceDebug } from '../shared/ResourceDebug';
import { Pivot, PivotItem } from '@fluentui/react';
import { ResourcePropertyPanel } from '../shared/ResourcePropertyPanel';
import { Resource } from '../../models/resource';
import { ResourceHistory } from '../shared/ResourceHistory';
import { ResourceOperationsList } from '../shared/ResourceOperationsList';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm'

interface ResourceBodyProps {
  resource: Resource,
  readonly?: boolean
}

export const ResourceBody: React.FunctionComponent<ResourceBodyProps> = (props: ResourceBodyProps) => {

  return (
    <Pivot aria-label="Resource Menu" className='tre-panel'>
      <PivotItem
        headerText="Overview"
        headerButtonProps={{
          'data-order': 1,
          'data-title': 'Overview',
        }}
      >
        <div style={{ padding: 5 }}>
          {props.readonly}
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{props.resource.properties?.overview || props.resource.properties?.description}</ReactMarkdown>
        </div>
      </PivotItem>
      {
        !props.readonly &&
        <PivotItem headerText="Details">
          <ResourcePropertyPanel resource={props.resource} />
          <ResourceDebug resource={props.resource} />
        </PivotItem>
      }
      {
        !props.readonly &&
        <PivotItem headerText="History">
          <ResourceHistory history={props.resource.history} />
        </PivotItem>
      }
      {
        !props.readonly &&
        <PivotItem headerText="Operations">
          <ResourceOperationsList resource={props.resource} />
        </PivotItem>
      }
    </Pivot>
  );
};

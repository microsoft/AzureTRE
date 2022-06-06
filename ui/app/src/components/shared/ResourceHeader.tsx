import React from 'react';
import { ProgressIndicator, Stack } from '@fluentui/react';
import { ResourceContextMenu } from '../shared/ResourceContextMenu';
import { ComponentAction, Resource } from '../../models/resource';

interface ResourceHeaderProps {
  resource: Resource,
  componentAction: ComponentAction
}

export const ResourceHeader: React.FunctionComponent<ResourceHeaderProps> = (props: ResourceHeaderProps) => {

  return (
    <>
      {props.resource && props.resource.id &&
        <div className="tre-panel">
          <Stack>
            <Stack.Item>
              <h1 style={{ margin: 0, paddingBottom: 10, borderBottom: '1px #999 solid' }}><span style={{ textTransform: 'capitalize' }}>{props.resource.resourceType.replace('-', ' ')}</span>: {props.resource.properties?.display_name}</h1>
            </Stack.Item>
            <Stack.Item>
              <ResourceContextMenu resource={props.resource} commandBar={true} componentAction={props.componentAction} />
            </Stack.Item>
            {
              props.componentAction === ComponentAction.Lock &&
              <Stack.Item>
                <ProgressIndicator description="Resource locked while it updates" />
              </Stack.Item>
            }
          </Stack>
        </div>
      }
    </>
  );
};

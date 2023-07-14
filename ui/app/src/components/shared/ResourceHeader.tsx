import React from 'react';
import { ProgressIndicator, Stack } from '@fluentui/react';
import { ResourceContextMenu } from '../shared/ResourceContextMenu';
import { ComponentAction, Resource, ResourceUpdate } from '../../models/resource';
import { StatusBadge } from './StatusBadge';
import { PowerStateBadge } from './PowerStateBadge';

interface ResourceHeaderProps {
  resource: Resource,
  latestUpdate: ResourceUpdate,
  readonly?: boolean
}

export const ResourceHeader: React.FunctionComponent<ResourceHeaderProps> = (props: ResourceHeaderProps) => {

  return (
    <>
      {props.resource && props.resource.id &&
        <div className="tre-panel">
          <Stack>
            <Stack.Item style={!props.readonly ? { borderBottom: '1px #999 solid' } : {}}>
              <Stack horizontal>
                <Stack.Item grow={1}>
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <h1 style={{ marginLeft: 5, marginTop: 5, marginRight: 15, marginBottom: 10 }}>
                      {props.resource.properties?.display_name}
                    </h1>
                    {
                      (props.resource.azureStatus?.powerState) &&
                      <PowerStateBadge state={props.resource.azureStatus.powerState} />
                    }
                  </div>
                </Stack.Item>
                {
                  (props.latestUpdate.operation || props.resource.deploymentStatus) &&
                  <Stack.Item align="center">
                    <StatusBadge
                      resource={props.resource}
                      status={
                        props.latestUpdate.operation?.status
                          ? props.latestUpdate.operation.status
                          : props.resource.deploymentStatus
                      }
                    />
                  </Stack.Item>
                }
              </Stack>
            </Stack.Item>
            {
              !props.readonly &&
              <Stack.Item>
                <ResourceContextMenu
                  resource={props.resource}
                  commandBar={true}
                  componentAction={props.latestUpdate.componentAction}
                />
              </Stack.Item>
            }

            {
              props.latestUpdate.componentAction === ComponentAction.Lock &&
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

import React, {  } from 'react';

import { IStackStyles, IStackTokens, Stack, Text } from '@fluentui/react';
import { ResourceCard } from '../shared/ResourceCard';
import { Resource } from '../../models/resource';

interface ResourceCardListProps {
  resources: Array<Resource>,
  selectResource?: (resource: Resource) => void,
  updateResource: (resource: Resource) => void,
  removeResource: (resource: Resource) => void
  emptyText: string,
  readonly?: boolean
}

export const ResourceCardList: React.FunctionComponent<ResourceCardListProps> = (props: ResourceCardListProps) => {

  return (
    <>
      {
        props.resources.length > 0 ?
          <Stack horizontal wrap styles={stackStyles} tokens={wrapStackTokens}>
            {
              props.resources.map((r:Resource, i:number) => {
                return (
                  <Stack.Item key={i} style={gridItemStyles} >
                    <ResourceCard
                      resource={r}
                      selectResource={(resource: Resource) => props.selectResource && props.selectResource(resource)}
                      onUpdate={(resource: Resource) => props.updateResource(resource)}
                      onDelete={(resource: Resource) => props.removeResource(resource)}
                      itemId={i}
                      readonly={props.readonly} />
                  </Stack.Item>
                )
              })
            }
          </Stack> :
          <Text variant="large" block>{props.emptyText}</Text>
      }
    </>
  );
};

const stackStyles: IStackStyles = {
  root: {
    width: 'calc(100% - 20px)'
  },
};

const wrapStackTokens: IStackTokens = { childrenGap: 20 };

const gridItemStyles: React.CSSProperties = {
  alignItems: 'left',
  display: 'flex',
  width: 300,
  background: '#f9f9f9'
};

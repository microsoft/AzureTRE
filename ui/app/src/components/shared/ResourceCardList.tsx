import React from 'react';

import { IStackStyles, IStackTokens, Stack, Text } from '@fluentui/react';
import { ResourceCard } from '../shared/ResourceCard';
import { Resource } from '../../models/resource';

interface ResourceCardListProps {
  resources: Array<Resource>,
  selectResource: (resource: Resource) => void,
  contextMenuElement?: JSX.Element,
  emptyText: string
}

export const ResourceCardList: React.FunctionComponent<ResourceCardListProps> = (props: ResourceCardListProps) => {

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

  return (
    <>
      {
        props.resources.length > 0 ?
          <Stack horizontal wrap styles={stackStyles} tokens={wrapStackTokens}>
            {
              props.resources.map((r, i) => {
                return (
                  <Stack.Item key={i} style={gridItemStyles} >
                    <ResourceCard resource={r} selectResource={() => props.selectResource(r)} itemId={i} contextMenuElement={props.contextMenuElement}/>
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

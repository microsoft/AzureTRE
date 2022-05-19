import * as React from 'react';
import { DefaultPalette, Stack, Text } from "@fluentui/react";
import { List } from '@fluentui/react/lib/List';
import { HistoryItem } from '../../models/resource';
import { ResourcePropertyPanelItem } from './ResourcePropertyPanel';

interface ResourceHistoryProps {
  history: Array<HistoryItem>
}

const headerStyles: React.CSSProperties = {
  padding: '5px 10px',
  fontSize: '1.3rem',
};

const bodyStyles: React.CSSProperties = {
  borderBottom: '1px #ccc solid',
  padding: '5px 10px',
  minHeight: '70px'
}

const footerStyles: React.CSSProperties = {
  backgroundColor: DefaultPalette.white,
  padding: '5px 10px',
  minHeight: '15px'
}

const onRenderCell = (item: any, index: number | undefined): JSX.Element => {
  var propertyBag = {...item.properties}
  delete propertyBag['display_name']
  delete propertyBag['description']

  function userFriendlyKey(key: String){
    let friendlyKey = key.replaceAll('_', ' ');
    return friendlyKey.charAt(0).toUpperCase() + friendlyKey.slice(1).toLowerCase();
  }

  return (
  <Stack wrap horizontal>
    <Stack grow>
    <Stack.Item style={headerStyles}>
      <Text>{item.properties.display_name}</Text>
      <Text>{item.updatedWhen}</Text>
      <Text>{item.resourceVersion}</Text>
      <Text>{item.isEnabled}</Text>
    </Stack.Item>
    <Stack.Item grow={3} style={bodyStyles}>
      <Text>
      {item.properties.description}
      {
        Object.keys(propertyBag).map((key) => {
            let val = (propertyBag as any)[key].toString();
            return (
              <ResourcePropertyPanelItem header={userFriendlyKey(key)} val={val} key={key}/>
            )
        })
      }
      </Text>
    </Stack.Item>
    <Stack.Item style={footerStyles}>
          &nbsp;
        </Stack.Item>
    </Stack>
  </Stack>
  );
};

export const ResourceHistory: React.FunctionComponent<ResourceHistoryProps> = (props: ResourceHistoryProps) => {
  return (
    <List items={props.history} onRenderCell={onRenderCell} />
  )
};
import * as React from 'react';
import { DetailsList, DetailsListLayoutMode, initializeIcons, IColumn, Text } from "@fluentui/react";
import { Icon } from '@fluentui/react/lib/Icon';
import { CheckboxVisibility } from "@fluentui/react/lib/DetailsList";
import { HistoryItem } from '../../models/resource';
import { ResourcePropertyPanelItem } from './ResourcePropertyPanel';
import moment from 'moment';

interface IResourceHistoryProps {
  history: HistoryItem[]
}

export const ResourceHistory: React.FunctionComponent<IResourceHistoryProps> = (props: IResourceHistoryProps) => {

  initializeIcons()

  const DisabledIcon = () => <Icon iconName="CirclePauseSolid" />;
  const EnabledIcon = () => <Icon iconName="CompletedSolid" />;

  function userFriendlyKey(key: string){
    let friendlyKey = key.replaceAll('_', ' ');
    return friendlyKey.charAt(0).toUpperCase() + friendlyKey.slice(1).toLowerCase();
  }

  function sortHistoryDescending(items: HistoryItem[]){
    return items.sort((a, b) => b.resourceVersion - a.resourceVersion);
  }

  const columns: IColumn[] = [
    {
      key: 'column1',
      name: 'Version',
      fieldName: 'resourceVersion',
      minWidth: 35,
      maxWidth: 40,
      isRowHeader: true,
      isResizable: true,
      isSorted: true,
      isSortedDescending: true,
      data: 'number',
      isPadded: true,
      onRender: (item: HistoryItem) => (
        <Text>{item.resourceVersion}</Text>
      ),
    },
    {
      key: 'column2',
      name: 'Name',
      fieldName: 'name',
      minWidth: 150,
      maxWidth: 200,
      isResizable: true,
      isMultiline: true,
      data: 'number',
      onRender: (item: HistoryItem) => {
        return <Text>{item.properties.display_name} ({item.properties.description})</Text>;
      },
      isPadded: true,
    },
    {
      key: 'column3',
      name: 'Properties',
      fieldName: 'properties',
      minWidth: 300,
      maxWidth: 350,
      isResizable: true,
      isCollapsible: true,
      isMultiline: true,
      data: 'string',
      onRender: (item: HistoryItem) => {
        var propertyBag = {...item.properties}
        delete propertyBag['display_name']
        delete propertyBag['description']

        return <Text>
          {
            Object.keys(propertyBag).map((key:any, i:number) => {
              let val = (propertyBag as any)[key].toString();
              return <ResourcePropertyPanelItem header={userFriendlyKey(key)} val={val} key={i}/>
            })
          }
          </Text>
      },
      isPadded: true,
    },
    {
      key: 'column5',
      name: 'Date Modified',
      fieldName: 'updatedWhen',
      minWidth: 90,
      maxWidth: 100,
      isResizable: true,
      isMultiline: true,
      data: 'string',
      onRender: (item: HistoryItem) => {
        return <Text>{`${moment.unix(item.updatedWhen).toLocaleString()} (${moment.unix(item.updatedWhen).fromNow()})`}</Text>;
      },
      isPadded: true,
    },
    {
      key: 'column6',
      name: 'Enabled',
      fieldName: 'isEnabled',
      minWidth: 20,
      maxWidth: 25,
      isResizable: true,
      isCollapsible: true,
      data: 'boolean',
      onRender: (item: HistoryItem) => {
        return item.isEnabled ? EnabledIcon() : DisabledIcon();
      },
      isPadded: true,
    }
  ];

  return (
    <DetailsList
      items={sortHistoryDescending(props.history)}
      checkboxVisibility={CheckboxVisibility.hidden}
      columns={columns}
      layoutMode={DetailsListLayoutMode.justified}
      isHeaderVisible={true}
    />
  )
};

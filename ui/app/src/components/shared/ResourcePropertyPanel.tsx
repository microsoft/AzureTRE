import { DefaultPalette, IStackItemStyles, IStackStyles, Stack } from "@fluentui/react";
import React from "react";
import { Resource } from "../../models/resource";
import { ResourceType } from "../../models/resourceType";
import { Workspace } from "../../models/workspace";

interface ResourcePanelProps {
    resource: Resource
}

interface ResourcePanelItemProps {
    header: String,
    val: String
}

const ResourcePropertyPanelItem: React.FunctionComponent<ResourcePanelItemProps> = (props: ResourcePanelItemProps) => {
    
    const stackItemStyles: IStackItemStyles = {
        root: {
            padding: 5,
            width: 150,
            color: DefaultPalette.neutralSecondary
        }
    }

    return(
        <>
            <Stack wrap horizontal>
                <Stack.Item grow styles={stackItemStyles}>
                    {props.header}
                </Stack.Item>
                <Stack.Item grow styles={stackItemStyles}>
                    : {props.val}
                </Stack.Item>
            </Stack>
        </>
    );
}

export const ResourcePropertyPanel: React.FunctionComponent<ResourcePanelProps> = (props: ResourcePanelProps) => {
    
    const stackStyles: IStackStyles = {
        root: {
            padding: 0,
            minWidth: 300
        }
    };

    return (
        <>
            <h3>Resource property panel - {props.resource.id}</h3>
            <Stack wrap horizontal>
                <Stack grow styles={stackStyles}>
                    <ResourcePropertyPanelItem header={'Resource ID'} val={props.resource.id} />
                    <ResourcePropertyPanelItem header={'Resource type'} val={props.resource.resourceType} />
                    <ResourcePropertyPanelItem header={'Resource path'} val={props.resource.resourcePath} />
                    <ResourcePropertyPanelItem header={'Template name'} val={props.resource.templateName} />
                    <ResourcePropertyPanelItem header={'Template version'} val={props.resource.templateVersion} />
                    <ResourcePropertyPanelItem header={'Is active'} val={props.resource.isActive.toString()} />
                    <ResourcePropertyPanelItem header={'Is enabled'} val={props.resource.isEnabled.toString()} />
                    <ResourcePropertyPanelItem header={'User'} val={props.resource.user.name} />
                </Stack>    
                { props.resource.resourceType === ResourceType.Workspace &&
                    <Stack grow styles={stackStyles}>
                        <ResourcePropertyPanelItem header={'Workspace Id'} val={props.resource.properties.workspace_id} />
                        <ResourcePropertyPanelItem header={'Display name'} val={props.resource.properties.display_name} />
                        <ResourcePropertyPanelItem header={'Description'} val={props.resource.properties.description} />
                        <ResourcePropertyPanelItem header={'App ID'} val={props.resource.properties.app_id} />
                        <ResourcePropertyPanelItem header={'Address space size'} val={props.resource.properties.address_space_size} />
                        <ResourcePropertyPanelItem header={'Azure location'} val={props.resource.properties.azure_location} />
                    </Stack>       
                }
            </Stack>
        </>
    );
};
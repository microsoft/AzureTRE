import { DefaultPalette, IStackItemStyles, IStackStyles, Stack } from "@fluentui/react";
import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Operation } from '../../models/operation';
import { Workspace } from '../../models/workspace';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { HttpMethod, ResultType, useAuthApiCall } from '../../useAuthApiCall';
import config from '../../config.json';



interface WorkspaceOperationPanelProps {
    workspace: Workspace
}

interface WorkspaceOperationPanelItemProps {
    header: String,
    val: String
}

const WorkspaceOperationPanelItem: React.FunctionComponent<WorkspaceOperationPanelItemProps> = (props: WorkspaceOperationPanelItemProps) => {



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

export const WorkspaceOperationsPanel: React.FunctionComponent<WorkspaceOperationPanelProps> = (props: WorkspaceOperationPanelProps) => {
    const { workspaceId } = useParams();
    const apiCall = useAuthApiCall();
    const [loadingState, setLoadingState] = useState('loading');

    const getOperations = async () => {
        try {
        let ws = props.workspace && props.workspace.id ?
        props.workspace :
        (await apiCall(`${ApiEndpoint.Workspaces}/${workspaceId}`, HttpMethod.Get)).workspace;

        await apiCall(`${ApiEndpoint.Workspaces}/${workspaceId}`, HttpMethod.Get, ws.properties.app_id, undefined, ResultType.None, (roles: Array<string>) => {
            config.debug && console.log(`Workspace roles for ${ws.properties?.display_name}`, roles);
        }, true);

        // get workspace operations 
        const workspaceOperations = await apiCall(`${ApiEndpoint.Workspaces}/${ws.id}/${ApiEndpoint.Operations}`, HttpMethod.Get, ws.properties.app_id);
        
        } catch {
            setLoadingState('error');
        }
    };
    getOperations();

    const stackStyles: IStackStyles = {
        root: {
            padding: 0,
            minWidth: 300
        }
    };

    return (
        <>
            <Stack wrap horizontal>
                <Stack grow styles={stackStyles}>

                    <WorkspaceOperationPanelItem header={'Resource Id'} val={props.workspace.id} />
                    {/* <WorkspaceOperationPanelItem header={'Resource Path'} val={props.operations.resourcePath} />
                    <WorkspaceOperationPanelItem header={'Resource Version'} val={props.operations.resourceVersion} />

                    <WorkspaceOperationPanelItem header={'Status'} val={props.operations.status} />
                    <WorkspaceOperationPanelItem header={'Action'} val={props.operations.action} />
                    <WorkspaceOperationPanelItem header={'Message'} val={props.operations.message} />
                    <WorkspaceOperationPanelItem header={'Created'} val={props.operations.createdWhen.toString()} />
                    <WorkspaceOperationPanelItem header={'Updated'} val={props.operations.updatedWhen.toString()} />
                    <WorkspaceOperationPanelItem header={'Message'} val={props.operations.message} />
                    <WorkspaceOperationPanelItem header={'User'} val={props.operations.user.name} /> */}
                </Stack>    
            </Stack>
        </>
    );
};
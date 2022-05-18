import { DefaultPalette, IStackItemStyles, IStackStyles, Stack } from "@fluentui/react";
import React, { useState } from 'react';
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
    const apiCall = useAuthApiCall();
    const { workspaceId } = useParams();
    const [workspaceOperations, setWorkspaceOperations] = useState([] as Array<Operation>)
    

    const getOperations = async () => {
        let ws = props.workspace && props.workspace.id ?
        props.workspace :
        (await apiCall(`${ApiEndpoint.Workspaces}/${workspaceId}`, HttpMethod.Get)).workspace;

        await apiCall(`${ApiEndpoint.Workspaces}/${workspaceId}`, HttpMethod.Get, ws.properties.app_id, undefined, ResultType.None, (roles: Array<string>) => {
            config.debug && console.log(`Workspace roles for ${ws.properties?.display_name}`, roles);
        }, true);

        // get workspace operations 
        config.debug && console.log(`Getting Workspace Operations for workspace:${props.workspace.id}`);
        const workspaceOperations = await apiCall(`${ApiEndpoint.Workspaces}/${ws.id}/${ApiEndpoint.Operations}`, HttpMethod.Get, ws.properties.app_id);
        config.debug && console.log(`Got Workspace Operations, for workspace:${props.workspace.id}: ${workspaceOperations.operations}`);
        setWorkspaceOperations(workspaceOperations.operations);
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
            {
                workspaceOperations && workspaceOperations.map((op:Operation) => {
                    return (
                        <Stack wrap horizontal>
                            <Stack grow styles={stackStyles}>
                                <WorkspaceOperationPanelItem header={'Resource Id'} val={op.resourceId} />
                                <WorkspaceOperationPanelItem header={'Resource Path'} val={op.resourcePath} />
                                <WorkspaceOperationPanelItem header={'Resource Version'} val={op.resourceVersion} />
                                <WorkspaceOperationPanelItem header={'Status'} val={op.status} />
                                <WorkspaceOperationPanelItem header={'Action'} val={op.action} />
                                <WorkspaceOperationPanelItem header={'Message'} val={op.message} />
                                <WorkspaceOperationPanelItem header={'Created'} val={new Date(op.createdWhen).toTimeString()} />
                                <WorkspaceOperationPanelItem header={'Updated'} val={new Date(op.updatedWhen).toTimeString()} />
                                <WorkspaceOperationPanelItem header={'Message'} val={op.message} />
                                <WorkspaceOperationPanelItem header={'User'} val={op.user.name} />
                            </Stack>    
                        </Stack>
                    )
                })
            }
        </>
    );
};
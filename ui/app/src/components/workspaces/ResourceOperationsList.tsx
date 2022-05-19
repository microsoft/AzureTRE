import { DefaultPalette, IStackItemStyles, IStackStyles, MessageBar, MessageBarType, Spinner, SpinnerSize, Stack } from "@fluentui/react";
import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { HttpMethod, useAuthApiCall } from '../../useAuthApiCall';
import { Operation } from '../../models/operation';
import { Resource } from '../../models/resource';
import { ApiEndpoint } from '../../models/apiEndpoints';
import config from '../../config.json';

interface ResourceOperationsListProps {
    resource: Resource
}   

interface ResourceOperationsListItemProps {
    header: String,
    val: String
}

const ResourceOperationsListItem: React.FunctionComponent<ResourceOperationsListItemProps> = (props: ResourceOperationsListItemProps) => {

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

export const ResourceOperationsList: React.FunctionComponent<ResourceOperationsListProps> = (props: ResourceOperationsListProps) => {
    const apiCall = useAuthApiCall();
    // const { workspaceId } = useParams();
    const { resourceId } = useParams();
    const [resourceOperations, setResourceOperations] = useState([] as Array<Operation>)
    const [loadingState, setLoadingState] = useState('loading');

    useEffect(() => {
        const getOperations = async () => {
            try {
                // let ws = props.workspace && props.workspace.id ?
                // props.workspace :
                // (await apiCall(`${ApiEndpoint.Workspaces}/${workspaceId}`, HttpMethod.Get)).workspace;
                let ws = props.resource && props.resource.id ?
                props.resource :
                (await apiCall(`/${props.resource.resourcePath}`, HttpMethod.Get)).workspace;
                
                // get resource operations 
                const resourceOperations = await apiCall(`${ApiEndpoint.Workspaces}/${ws.id}/${ApiEndpoint.Operations}`, HttpMethod.Get, ws.properties.app_id);
                // const resourceOperations = await apiCall(`/${resource.resourcePath}/${ApiEndpoint.Operations}`, HttpMethod.Get, ws.properties.app_id);
                  
                setLoadingState(resourceOperations && resourceOperations.operations.length > 0 ? 'ok' : 'error');

                config.debug && console.log(`Got resource operations, for resource:${props.resource.id}: ${resourceOperations.operations}`);
                setResourceOperations(resourceOperations.operations);
            } catch {
                setLoadingState('error');
            }
        };
        getOperations();
    }, [apiCall, props.resource, resourceId]);

    
    const stackStyles: IStackStyles = {
        root: {
            padding: 0,
            minWidth: 300
        }
    };

    switch (loadingState) {
        case 'ok':
            return (
                <>
                    {
                        resourceOperations && resourceOperations.map((op:Operation) => {
                            return (
                                <Stack wrap horizontal>
                                    <Stack grow styles={stackStyles}>
                                        <ResourceOperationsListItem header={'Resource Id'} val={op.resourceId} />
                                        <ResourceOperationsListItem header={'Resource Path'} val={op.resourcePath} />
                                        <ResourceOperationsListItem header={'Resource Version'} val={op.resourceVersion} />
                                        <ResourceOperationsListItem header={'Status'} val={op.status} />
                                        <ResourceOperationsListItem header={'Action'} val={op.action} />
                                        <ResourceOperationsListItem header={'Message'} val={op.message} />
                                        <ResourceOperationsListItem header={'Created'} val={new Date(op.createdWhen).toTimeString()} />
                                        <ResourceOperationsListItem header={'Updated'} val={new Date(op.updatedWhen).toTimeString()} />
                                        <ResourceOperationsListItem header={'User'} val={op.user.name} />
                                    </Stack>    
                                </Stack>
                            )
                        })
                    }
                </>
            );
        case 'error':
            return (
                <MessageBar
                messageBarType={MessageBarType.error}
                isMultiline={true}
                >
                <h3>Error retrieving resource operations</h3>
                <p>There was an error retrieving this resource operations. Please see the browser console for details.</p>
                </MessageBar>
            )
        default:
            return (
                <div style={{ marginTop: '20px' }}>
                <Spinner label="Loading operations" ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
                </div>
            )
        }
    };
    
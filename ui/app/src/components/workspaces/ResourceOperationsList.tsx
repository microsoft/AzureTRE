import { IStackStyles, MessageBar, MessageBarType, Spinner, SpinnerSize, Stack } from "@fluentui/react";
import React, { useEffect, useContext, useState } from 'react';
import { useParams } from 'react-router-dom';
import { HttpMethod, useAuthApiCall } from '../../useAuthApiCall';
import { Operation } from '../../models/operation';
import { Resource } from '../../models/resource';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { ResourceOperationListItem } from './ResourceOperationListItem';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import config from '../../config.json';


interface ResourceOperationsListProps {
    resource: Resource
}   

export const ResourceOperationsList: React.FunctionComponent<ResourceOperationsListProps> = (props: ResourceOperationsListProps) => {
    const apiCall = useAuthApiCall();
    const workspaceCtx = useContext(WorkspaceContext);
    const { resourceId } = useParams();
    const [resourceOperations, setResourceOperations] = useState([] as Array<Operation>)
    const [loadingState, setLoadingState] = useState('loading');

    useEffect(() => {
        const getOperations = async () => {
            try {
                // get resource operations 
                const resourceOperations = await apiCall(`${ApiEndpoint.Workspaces}/${props.resource.id}/${ApiEndpoint.Operations}`, HttpMethod.Get, workspaceCtx.workspaceClientId);
                config.debug && console.log(`Got resource operations, for resource:${props.resource.id}: ${resourceOperations.operations}`);
                setResourceOperations(resourceOperations.operations);
                setLoadingState(resourceOperations && resourceOperations.operations.length > 0 ? 'ok' : 'error');
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
                                        <ResourceOperationListItem header={'Resource Id'} val={op.resourceId} />
                                        <ResourceOperationListItem header={'Resource Path'} val={op.resourcePath} />
                                        <ResourceOperationListItem header={'Resource Version'} val={op.resourceVersion.toString()} />
                                        <ResourceOperationListItem header={'Status'} val={op.status} />
                                        <ResourceOperationListItem header={'Action'} val={op.action} />
                                        <ResourceOperationListItem header={'Message'} val={op.message} />
                                        <ResourceOperationListItem header={'Created'} val={new Date(op.createdWhen).toTimeString()} />
                                        <ResourceOperationListItem header={'Updated'} val={new Date(op.updatedWhen).toTimeString()} />
                                        <ResourceOperationListItem header={'User'} val={op.user.name} />
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
    
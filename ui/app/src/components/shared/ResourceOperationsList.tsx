import { IStackStyles, Spinner, SpinnerSize, Stack } from "@fluentui/react";
import React, { useEffect, useContext, useState } from 'react';
import { useParams } from 'react-router-dom';
import { HttpMethod, useAuthApiCall } from '../../hooks/useAuthApiCall';
import { Operation } from '../../models/operation';
import { Resource } from '../../models/resource';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { ResourceOperationListItem } from './ResourceOperationListItem';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import config from '../../config.json';
import moment from "moment";
import { APIError } from "../../models/exceptions";
import { LoadingState } from "../../models/loadingState";
import { ExceptionLayout } from "./ExceptionLayout";


interface ResourceOperationsListProps {
  resource: Resource
}

export const ResourceOperationsList: React.FunctionComponent<ResourceOperationsListProps> = (props: ResourceOperationsListProps) => {
  const apiCall = useAuthApiCall();
  const [apiError, setApiError] = useState({} as APIError);
  const workspaceCtx = useContext(WorkspaceContext);
  const { resourceId } = useParams();
  const [resourceOperations, setResourceOperations] = useState([] as Array<Operation>)
  const [loadingState, setLoadingState] = useState('loading');

  useEffect(() => {
    const getOperations = async () => {
      try {
        // get resource operations
        const ops = await apiCall(`${props.resource.resourcePath}/${ApiEndpoint.Operations}`, HttpMethod.Get, workspaceCtx.workspaceApplicationIdURI);
        config.debug && console.log(`Got resource operations, for resource:${props.resource.id}: ${ops.operations}`);
        setResourceOperations(ops.operations.reverse());
        setLoadingState(ops && ops.operations.length > 0 ? LoadingState.Ok : LoadingState.Error);
      } catch (err: any) {
        err.userMessage = "Error retrieving resource operations"
        setApiError(err);
        setLoadingState(LoadingState.Error);
      }
    };
    getOperations();
  }, [apiCall, props.resource, resourceId, workspaceCtx.workspaceApplicationIdURI]);


  const stackStyles: IStackStyles = {
    root: {
      padding: 0,
      minWidth: 300
    }
  };

  switch (loadingState) {
    case LoadingState.Ok:
      return (
        <>
          {
            resourceOperations && resourceOperations.map((op: Operation, i: number) => {
              return (
                <Stack wrap horizontal style={{borderBottom: '1px #999 solid', padding: '10px 0'}} key={i}>
                  <Stack grow styles={stackStyles}>
                    <ResourceOperationListItem header={'Resource Id'} val={op.resourceId} />
                    <ResourceOperationListItem header={'Resource Path'} val={op.resourcePath} />
                    <ResourceOperationListItem header={'Resource Version'} val={op.resourceVersion.toString()} />
                    <ResourceOperationListItem header={'Status'} val={op.status} />
                    <ResourceOperationListItem header={'Action'} val={op.action} />
                    <ResourceOperationListItem header={'Message'} val={op.message} />
                    <ResourceOperationListItem header={'Created'} val={`${moment.unix(op.createdWhen).toLocaleString()} (${moment.unix(op.createdWhen).fromNow()})`} />
                    <ResourceOperationListItem header={'Updated'} val={`${moment.unix(op.updatedWhen).toLocaleString()} (${moment.unix(op.updatedWhen).fromNow()})`} />
                    <ResourceOperationListItem header={'User'} val={op.user.name} />
                  </Stack>
                </Stack>
              )
            })
          }
        </>
      );
    case LoadingState.Error:
      return (
        <ExceptionLayout e={apiError} />
      )
    default:
      return (
        <div style={{ marginTop: '20px' }}>
          <Spinner label="Loading operations" ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
        </div>
      )
  }
};

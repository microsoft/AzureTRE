import { IStackStyles, Spinner, SpinnerSize, Stack } from "@fluentui/react";
import React, { useEffect, useContext, useState } from 'react';
import { useParams } from 'react-router-dom';
import { HttpMethod, useAuthApiCall } from '../../hooks/useAuthApiCall';
import { HistoryItem, Resource } from '../../models/resource';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { ResourceHistoryListItem } from './ResourceHistoryListItem';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import config from '../../config.json';
import moment from "moment";
import { APIError } from "../../models/exceptions";
import { LoadingState } from "../../models/loadingState";
import { ExceptionLayout } from "./ExceptionLayout";


interface ResourceHistoryListProps {
  resource: Resource
}

export const ResourceHistoryList: React.FunctionComponent<ResourceHistoryListProps> = (props: ResourceHistoryListProps) => {
  const apiCall = useAuthApiCall();
  const [apiError, setApiError] = useState({} as APIError);
  const workspaceCtx = useContext(WorkspaceContext);
  const { resourceId } = useParams();
  const [resourceHistory, setResourceHistory] = useState([] as Array<HistoryItem>)
  const [loadingState, setLoadingState] = useState('loading');

  useEffect(() => {
    const getResourceHistory = async () => {
      try {
        // get resource operations
        const scopeId = workspaceCtx.roles.length > 0 ? workspaceCtx.workspaceApplicationIdURI : "";
        const history = await apiCall(`${props.resource.resourcePath}/${ApiEndpoint.History}`, HttpMethod.Get, scopeId);
        config.debug && console.log(`Got resource history, for resource:${props.resource.id}: ${history.resource_history}`);
        setResourceHistory(history.resource_history.reverse());
        setLoadingState(history ? LoadingState.Ok : LoadingState.Error);
      } catch (err: any) {
        err.userMessage = "Error retrieving resource history"
        setApiError(err);
        setLoadingState(LoadingState.Error);
      }
    };
    getResourceHistory();
  }, [apiCall, props.resource, resourceId, workspaceCtx.workspaceApplicationIdURI, workspaceCtx.roles]);


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
            resourceHistory && resourceHistory.map((history: HistoryItem, i: number) => {
              return (
                <Stack wrap horizontal style={{borderBottom: '1px #999 solid', padding: '10px 0'}} key={i}>
                  <Stack grow styles={stackStyles}>
                    <ResourceHistoryListItem header={'Resource Id'} val={history.resourceId} />
                    <ResourceHistoryListItem header={'Resource Version'} val={history.resourceVersion.toString()} />
                    <ResourceHistoryListItem header={'Enabled'} val={history.isEnabled.toString()} />
                    <ResourceHistoryListItem header={'Template Version'} val={history.templateVersion} />
                    <ResourceHistoryListItem header={'Updated'} val={`${moment.unix(history.updatedWhen).toLocaleString()} (${moment.unix(history.updatedWhen).fromNow()})`} />
                    <ResourceHistoryListItem header={'User'} val={history.user.name} />
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
          <Spinner label="Loading history" ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
        </div>
      )
  }
};

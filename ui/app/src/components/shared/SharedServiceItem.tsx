import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { useAuthApiCall, HttpMethod } from '../../hooks/useAuthApiCall';
import { ResourceDebug } from '../shared/ResourceDebug';
import { MessageBar, MessageBarType, Pivot, PivotItem, Spinner, SpinnerSize } from '@fluentui/react';
import { ResourcePropertyPanel } from '../shared/ResourcePropertyPanel';
import { LoadingState } from '../../models/loadingState';
import { SharedService } from '../../models/sharedService';
import { ResourceHistory } from './ResourceHistory';
import { ResourceHeader } from './ResourceHeader';
import { ComponentAction } from '../../models/resource';
import { ResourceOperationsList } from './ResourceOperationsList';

export const SharedServiceItem: React.FunctionComponent = () => {
  const { sharedServiceId } = useParams();
  const [sharedService, setSharedService] = useState({} as SharedService);
  const [loadingState, setLoadingState] = useState(LoadingState.Loading);
  const apiCall = useAuthApiCall();

  useEffect(() => {
    const getData = async () => {
      let ss = await apiCall(`${ApiEndpoint.SharedServices}/${sharedServiceId}`, HttpMethod.Get);
      setSharedService(ss.sharedService);
      setLoadingState(LoadingState.Ok);
    };
    getData();
  }, [apiCall, sharedServiceId]);

  switch (loadingState) {
    case LoadingState.Ok:
      return (
        <>
          <ResourceHeader resource={sharedService} componentAction={ComponentAction.None} />
          <Pivot aria-label="Basic Pivot Example" className='tre-panel'>
            <PivotItem
              headerText="Overview"
              headerButtonProps={{
                'data-order': 1,
                'data-title': 'Overview',
              }}
            >
              <ResourcePropertyPanel resource={sharedService} />
              <ResourceDebug resource={sharedService} />
            </PivotItem>
            <PivotItem headerText="History">
              <ResourceHistory history={sharedService.history} />
            </PivotItem>
            <PivotItem headerText="Operations">
              <ResourceOperationsList resource={sharedService} />
            </PivotItem>
          </Pivot>
        </>
      );
    case LoadingState.Error:
      return (
        <MessageBar
          messageBarType={MessageBarType.error}
          isMultiline={true}
        >
          <h3>Error retrieving shared service</h3>
          <p>There was an error retrieving this shared service. Please see the browser console for details.</p>
        </MessageBar>
      );
    default:
      return (
        <div style={{ marginTop: '20px' }}>
          <Spinner label="Loading Shared Service" ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
        </div>
      )
  }
};

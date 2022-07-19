import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { useAuthApiCall, HttpMethod } from '../../hooks/useAuthApiCall';
import { MessageBar, MessageBarType, Spinner, SpinnerSize } from '@fluentui/react';
import { LoadingState } from '../../models/loadingState';
import { SharedService } from '../../models/sharedService';
import { ResourceHeader } from './ResourceHeader';
import { useComponentManager } from '../../hooks/useComponentManager';
import { Resource } from '../../models/resource';
import { ResourceBody } from './ResourceBody';

interface SharedServiceItemProps {
  readonly?: boolean
}

export const SharedServiceItem: React.FunctionComponent<SharedServiceItemProps> = (props: SharedServiceItemProps) => {
  const { sharedServiceId } = useParams();
  const [sharedService, setSharedService] = useState({} as SharedService);
  const [loadingState, setLoadingState] = useState(LoadingState.Loading);
  const navigate = useNavigate();

  const latestUpdate = useComponentManager(
    sharedService,
    (r: Resource) => setSharedService(r as SharedService),
    (r: Resource) => navigate(`/${ApiEndpoint.SharedServices}`)
  );
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
          <ResourceHeader resource={sharedService} latestUpdate={latestUpdate} readonly={props.readonly} />
          <ResourceBody resource={sharedService} readonly={props.readonly} />
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

import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { useAuthApiCall, HttpMethod } from '../../hooks/useAuthApiCall';
import { Spinner, SpinnerSize } from '@fluentui/react';
import { LoadingState } from '../../models/loadingState';
import { SharedService } from '../../models/sharedService';
import { ResourceHeader } from './ResourceHeader';
import { useComponentManager } from '../../hooks/useComponentManager';
import { Resource } from '../../models/resource';
import { ResourceBody } from './ResourceBody';
import { APIError } from '../../models/exceptions';
import { ExceptionLayout } from './ExceptionLayout';

interface SharedServiceItemProps {
  readonly?: boolean
}

export const SharedServiceItem: React.FunctionComponent<SharedServiceItemProps> = (props: SharedServiceItemProps) => {
  const { sharedServiceId } = useParams();
  const [sharedService, setSharedService] = useState({} as SharedService);
  const [loadingState, setLoadingState] = useState(LoadingState.Loading);
  const navigate = useNavigate();
  const apiCall = useAuthApiCall();
  const [apiError, setApiError] = useState({} as APIError);

  const latestUpdate = useComponentManager(
    sharedService,
    (r: Resource) => setSharedService(r as SharedService),
    (r: Resource) => navigate(`/${ApiEndpoint.SharedServices}`)
  );

  useEffect(() => {
    const getData = async () => {
      try {
        let ss = await apiCall(`${ApiEndpoint.SharedServices}/${sharedServiceId}`, HttpMethod.Get);
        setSharedService(ss.sharedService);
        setLoadingState(LoadingState.Ok);
      } catch (err:any) {
        err.userMessage = "Error retrieving shared service";
        setApiError(err);
        setLoadingState(LoadingState.Error)
      }
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
        <ExceptionLayout e={apiError} />
      );
    default:
      return (
        <div style={{ marginTop: '20px' }}>
          <Spinner label="Loading Shared Service" ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
        </div>
      )
  }
};

import React, { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ApiEndpoint } from "../../models/apiEndpoints";
import { useAuthApiCall, HttpMethod } from "../../hooks/useAuthApiCall";
import { Spinner, SpinnerSize } from "@fluentui/react";
import { LoadingState } from "../../models/loadingState";
import { SharedService } from "../../models/sharedService";
import { ResourceHeader } from "./ResourceHeader";
import { useComponentManager } from "../../hooks/useComponentManager";
import { Resource } from "../../models/resource";
import { ResourceBody } from "./ResourceBody";
import { APIError, isRetryableApiError } from "../../models/exceptions";
import { ExceptionLayout } from "./ExceptionLayout";
import { useRefresh } from "../../hooks/useRefresh";

interface SharedServiceItemProps {
  readonly?: boolean;
}

export const SharedServiceItem: React.FunctionComponent<SharedServiceItemProps> = (props: SharedServiceItemProps) => {
  const { sharedServiceId } = useParams();
  const [sharedService, setSharedService] = useState({} as SharedService);
  const [loadingState, setLoadingState] = useState(LoadingState.Loading);
  const navigate = useNavigate();
  const apiCall = useAuthApiCall();
  const [apiError, setApiError] = useState({} as APIError);
  const [refreshKey, setRefreshKey] = useState(0);
  const hasLoaded = useRef(false);
  const refresh = useRefresh(() => setRefreshKey((key) => key + 1));

  const latestUpdate = useComponentManager(
    sharedService,
    (r: Resource) => setSharedService(r as SharedService),
    (r: Resource) => navigate(`/${ApiEndpoint.SharedServices}`),
  );

  useEffect(() => {
    const getData = async () => {
      try {
        let ss = await apiCall(`${ApiEndpoint.SharedServices}/${sharedServiceId}`, HttpMethod.Get);
        setSharedService(ss.sharedService);
        hasLoaded.current = true;
        setLoadingState(LoadingState.Ok);
      } catch (err: any) {
        if (hasLoaded.current && isRetryableApiError(err)) {
          return;
        }
        err.userMessage = "Error retrieving shared service";
        setApiError(err);
        setLoadingState(LoadingState.Error);
      }
    };
    getData();
  }, [apiCall, sharedServiceId, refreshKey]);

  switch (loadingState) {
    case LoadingState.Ok:
      return (
        <>
          <ResourceHeader
            resource={sharedService}
            latestUpdate={latestUpdate}
            readonly={props.readonly}
            onRefresh={refresh}
          />
          <ResourceBody resource={sharedService} readonly={props.readonly} />
        </>
      );
    case LoadingState.Error:
      return <ExceptionLayout e={apiError} onRetry={refresh} />;
    default:
      return (
        <div style={{ marginTop: "20px" }}>
          <Spinner label="Loading Shared Service" ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
        </div>
      );
  }
};

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
  const loadedServiceId = useRef<string | undefined>(undefined);
  const errorServiceId = useRef<string | undefined>(undefined);
  const refresh = useRefresh(() => setRefreshKey((key) => key + 1));

  const latestUpdate = useComponentManager(
    sharedService,
    (r: Resource) => setSharedService(r as SharedService),
    (r: Resource) => navigate(`/${ApiEndpoint.SharedServices}`),
  );

  useEffect(() => {
    let cancelled = false;
    const getData = async () => {
      try {
        let ss = await apiCall(`${ApiEndpoint.SharedServices}/${sharedServiceId}`, HttpMethod.Get);
        if (cancelled) return;
        setSharedService(ss.sharedService);
        loadedServiceId.current = sharedServiceId;
        errorServiceId.current = undefined;
        setApiError({} as APIError);
        setLoadingState(LoadingState.Ok);
      } catch (err: any) {
        if (cancelled) return;
        if (loadedServiceId.current === sharedServiceId && isRetryableApiError(err)) {
          return;
        }
        errorServiceId.current = sharedServiceId;
        err.userMessage = "Error retrieving shared service";
        setApiError(err);
        setLoadingState(LoadingState.Error);
      }
    };
    getData();
    return () => {
      cancelled = true;
    };
  }, [apiCall, sharedServiceId, refreshKey]);

  const currentLoadingState =
    loadingState === LoadingState.Error && errorServiceId.current !== sharedServiceId
      ? loadedServiceId.current === sharedServiceId
        ? LoadingState.Ok
        : LoadingState.Loading
      : loadingState === LoadingState.Ok && loadedServiceId.current !== sharedServiceId
        ? LoadingState.Loading
        : loadingState;

  switch (currentLoadingState) {
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

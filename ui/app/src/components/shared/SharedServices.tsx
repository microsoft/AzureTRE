import React, { useContext, useEffect, useRef, useState } from "react";
import { Resource } from "../../models/resource";
import { ResourceCardList } from "../shared/ResourceCardList";
import { PrimaryButton, Stack, Spinner, SpinnerSize } from "@fluentui/react";
import { ResourceType } from "../../models/resourceType";
import { SharedService } from "../../models/sharedService";
import { HttpMethod, useAuthApiCall } from "../../hooks/useAuthApiCall";
import { LoadingState } from "../../models/loadingState";
import { ApiEndpoint } from "../../models/apiEndpoints";
import { CreateUpdateResourceContext } from "../../contexts/CreateUpdateResourceContext";
import { RoleName } from "../../models/roleNames";
import { SecuredByRole } from "./SecuredByRole";
import { useRefresh } from "../../hooks/useRefresh";
import { RefreshButton } from "./RefreshButton";
import { defaultSortOptions, ResourceListControls, useResourceListFilter } from "./ResourceListControls";
import { APIError, isRetryableApiError } from "../../models/exceptions";
import { ExceptionLayout } from "./ExceptionLayout";

const sortOptions = defaultSortOptions<SharedService>();

interface SharedServiceProps {
  readonly?: boolean;
}

export const SharedServices: React.FunctionComponent<SharedServiceProps> = (props: SharedServiceProps) => {
  const createFormCtx = useContext(CreateUpdateResourceContext);
  const [sharedServices, setSharedServices] = useState([] as Array<SharedService>);
  const [loadingState, setLoadingState] = useState(LoadingState.Loading);
  const [apiError, setApiError] = useState<APIError>();
  const [refreshKey, setRefreshKey] = useState(0);
  const hasLoaded = useRef(false);
  const requestGeneration = useRef(0);
  const { visibleResources, controlsProps } = useResourceListFilter(sharedServices, {
    storageKey: "shared-service",
    sortOptions,
  });
  const apiCall = useAuthApiCall();
  const refresh = useRefresh(() => setRefreshKey((key) => key + 1));

  useEffect(() => {
    let cancelled = false;
    const requestId = ++requestGeneration.current;
    const getSharedServices = async () => {
      try {
        const ss = (await apiCall(ApiEndpoint.SharedServices, HttpMethod.Get)).sharedServices;
        if (cancelled || requestId !== requestGeneration.current) return;
        setSharedServices(ss);
        setApiError(undefined);
        hasLoaded.current = true;
        setLoadingState(LoadingState.Ok);
      } catch (err) {
        if (cancelled || requestId !== requestGeneration.current) return;
        if (hasLoaded.current && isRetryableApiError(err)) {
          return;
        }
        const error = err as APIError;
        error.userMessage = error.userMessage || "Error loading shared services";
        setApiError(error);
        setLoadingState(LoadingState.Error);
      }
    };
    getSharedServices();
    return () => {
      cancelled = true;
    };
  }, [apiCall, refreshKey]);

  const updateSharedService = (ss: SharedService) => {
    let ssList = [...sharedServices];
    let i = ssList.findIndex((f: SharedService) => f.id === ss.id);
    ssList.splice(i, 1, ss);
    setSharedServices(ssList);
  };

  const removeSharedService = (ss: SharedService) => {
    let ssList = [...sharedServices];
    let i = ssList.findIndex((f: SharedService) => f.id === ss.id);
    ssList.splice(i, 1);
    setSharedServices(ssList);
  };

  const addSharedService = (ss: SharedService) => {
    let ssList = [...sharedServices];
    ssList.push(ss);
    setSharedServices(ssList);
  };

  switch (loadingState) {
    case LoadingState.Ok:
      return (
        <Stack className="tre-panel">
          <Stack.Item>
            <Stack horizontal horizontalAlign="space-between" verticalAlign="center">
              <h1>Shared Services</h1>
              <Stack horizontal verticalAlign="center" tokens={{ childrenGap: 8 }}>
                {!props.readonly && (
                  <SecuredByRole
                    allowedAppRoles={[RoleName.TREAdmin]}
                    element={
                      <PrimaryButton
                        iconProps={{ iconName: "Add" }}
                        text="Create new"
                        onClick={() => {
                          createFormCtx.openCreateForm({
                            resourceType: ResourceType.SharedService,
                            onAdd: (r: Resource) => addSharedService(r as SharedService),
                          });
                        }}
                      />
                    }
                  />
                )}
                <RefreshButton onClick={refresh} />
              </Stack>
            </Stack>
          </Stack.Item>
          <Stack.Item>
            <ResourceListControls
              {...controlsProps}
              searchPlaceholder="Search shared services by name, ID or status..."
              ariaLabel="Shared service list controls"
            />
          </Stack.Item>
          <Stack.Item>
            <ResourceCardList
              resources={visibleResources}
              updateResource={(r: Resource) => updateSharedService(r as SharedService)}
              removeResource={(r: Resource) => removeSharedService(r as SharedService)}
              emptyText={
                controlsProps.search
                  ? `No shared services found matching "${controlsProps.search}".`
                  : "This TRE has no shared services."
              }
              readonly={props.readonly}
            />
          </Stack.Item>
        </Stack>
      );
    case LoadingState.Error:
      return apiError ? <ExceptionLayout e={apiError} onRetry={refresh} /> : null;
    default:
      return (
        <div style={{ marginTop: "20px" }}>
          <Spinner label="Loading Shared Services" ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
        </div>
      );
  }
};

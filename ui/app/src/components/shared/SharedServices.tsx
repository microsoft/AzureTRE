import React, { useContext, useEffect, useState } from "react";
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

interface SharedServiceProps {
  readonly?: boolean;
}

export const SharedServices: React.FunctionComponent<SharedServiceProps> = (
  props: SharedServiceProps,
) => {
  const createFormCtx = useContext(CreateUpdateResourceContext);
  const [sharedServices, setSharedServices] = useState(
    [] as Array<SharedService>,
  );
  const [loadingState, setLoadingState] = useState(LoadingState.Loading);
  const apiCall = useAuthApiCall();

  useEffect(() => {
    const getSharedServices = async () => {
      try {
        const ss = (await apiCall(ApiEndpoint.SharedServices, HttpMethod.Get))
          .sharedServices;
        setSharedServices(ss);
        setLoadingState(LoadingState.Ok);
      } catch (err) {
        setLoadingState(LoadingState.Error);
      }
    };
    getSharedServices();
  }, [apiCall]);

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
            <Stack horizontal horizontalAlign="space-between">
              <h1>Shared Services</h1>
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
                          onAdd: (r: Resource) =>
                            addSharedService(r as SharedService),
                        });
                      }}
                    />
                  }
                />
              )}
            </Stack>
          </Stack.Item>
          <Stack.Item>
            <ResourceCardList
              resources={sharedServices}
              updateResource={(r: Resource) =>
                updateSharedService(r as SharedService)
              }
              removeResource={(r: Resource) =>
                removeSharedService(r as SharedService)
              }
              emptyText="This TRE has no shared services."
              readonly={props.readonly}
            />
          </Stack.Item>
        </Stack>
      );
    case LoadingState.Error:
      return (
        <div style={{ marginTop: "20px" }}>
          <span>Error loading shared services</span>
        </div>
      );
    default:
      return (
        <div style={{ marginTop: "20px" }}>
          <Spinner
            label="Loading shared services"
            ariaLive="assertive"
            labelPosition="top"
            size={SpinnerSize.large}
          />
        </div>
      );
  }
};

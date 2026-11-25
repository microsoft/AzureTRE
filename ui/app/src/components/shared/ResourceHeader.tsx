import React, { useEffect, useState } from "react";
import { PrimaryButton, ProgressIndicator, Stack } from "@fluentui/react";
import { ResourceContextMenu } from "../shared/ResourceContextMenu";
import { actionsDisabledStates } from "../../models/operation";
import { ComponentAction, Resource, ResourceUpdate, VMPowerStates } from "../../models/resource";
import { RefreshButton } from "./RefreshButton";
import { StatusBadge } from "./StatusBadge";
import { PowerStateBadge } from "./PowerStateBadge";
import { SecuredByRole } from "./SecuredByRole";
import { RoleName, WorkspaceRoleName } from "../../models/roleNames";
import { ResourceType } from "../../models/resourceType";
import { ConfirmCopyUrlToClipboard } from "./ConfirmCopyUrlToClipboard";
import { VMPowerButton } from "./VMPowerButton";
import { openExternalUrl } from "../../utils/openExternalUrl";

interface ResourceHeaderProps {
  resource: Resource;
  latestUpdate: ResourceUpdate;
  readonly?: boolean;
  isExposedExternally?: boolean;
  onRefresh?: () => void;
}

export const ResourceHeader: React.FunctionComponent<ResourceHeaderProps> = (props: ResourceHeaderProps) => {
  const [showCopyUrl, setShowCopyUrl] = useState(false);
  // The header is reused when a detail route switches resource; don't carry an open Connect dialog over to it.
  const resourceId = props.resource?.id;
  useEffect(() => setShowCopyUrl(false), [resourceId]);
  const connectionUri = props.resource.properties?.connection_uri;
  const isExposedExternally = props.resource.properties?.is_exposed_externally ?? props.isExposedExternally ?? true;
  const canConnect =
    props.latestUpdate.componentAction !== ComponentAction.Lock &&
    !actionsDisabledStates.includes(props.resource.deploymentStatus) &&
    props.resource.isEnabled &&
    (!props.resource.azureStatus?.powerState || props.resource.azureStatus.powerState === VMPowerStates.Running);
  const allowedWorkspaceRoles =
    props.resource.resourceType === ResourceType.SharedService
      ? [WorkspaceRoleName.WorkspaceOwner]
      : [WorkspaceRoleName.WorkspaceOwner, WorkspaceRoleName.WorkspaceResearcher, WorkspaceRoleName.AirlockManager];
  const allowedAppRoles =
    props.resource.resourceType === ResourceType.SharedService || props.resource.resourceType === ResourceType.Workspace
      ? [RoleName.TREAdmin]
      : [];

  return (
    <>
      {props.resource && props.resource.id && (
        <div className="tre-panel">
          <Stack>
            <Stack.Item style={!props.readonly ? { borderBottom: "1px #999 solid" } : {}}>
              <Stack horizontal>
                <Stack.Item grow={1}>
                  <div style={{ display: "flex", alignItems: "center" }}>
                    <h1
                      style={{
                        marginLeft: 5,
                        marginTop: 5,
                        marginRight: 15,
                        marginBottom: 10,
                      }}
                    >
                      {props.resource.properties?.display_name}
                    </h1>
                    {props.resource.azureStatus?.powerState && (
                      <PowerStateBadge state={props.resource.azureStatus.powerState} />
                    )}
                  </div>
                </Stack.Item>
                {(props.latestUpdate.operation || props.resource.deploymentStatus) && (
                  <Stack.Item align="center">
                    <StatusBadge
                      resource={props.resource}
                      status={
                        props.latestUpdate.operation?.status
                          ? props.latestUpdate.operation.status
                          : props.resource.deploymentStatus
                      }
                    />
                  </Stack.Item>
                )}
              </Stack>
            </Stack.Item>
            {(!props.readonly || props.onRefresh) && (
              <Stack.Item>
                <Stack horizontal verticalAlign="center" tokens={{ childrenGap: 8 }}>
                  {connectionUri && (
                    <SecuredByRole
                      allowedAppRoles={allowedAppRoles}
                      allowedWorkspaceRoles={allowedWorkspaceRoles}
                      element={
                        <PrimaryButton
                          text="Connect"
                          disabled={!canConnect}
                          title={
                            canConnect
                              ? "Connect to resource"
                              : "Resource must be enabled, successfully deployed, and powered on to connect"
                          }
                          onClick={() => (isExposedExternally ? openExternalUrl(connectionUri) : setShowCopyUrl(true))}
                        />
                      }
                    />
                  )}
                  {!props.readonly && (
                    <VMPowerButton resource={props.resource} componentAction={props.latestUpdate.componentAction} />
                  )}
                  <Stack.Item grow>
                    {!props.readonly && (
                      <ResourceContextMenu
                        resource={props.resource}
                        commandBar={true}
                        componentAction={props.latestUpdate.componentAction}
                        isExposedExternally={props.isExposedExternally}
                      />
                    )}
                  </Stack.Item>
                  {props.onRefresh && <RefreshButton onClick={props.onRefresh} />}
                </Stack>
              </Stack.Item>
            )}

            {props.latestUpdate.componentAction === ComponentAction.Lock && (
              <Stack.Item>
                <ProgressIndicator description="Resource locked while it updates" />
              </Stack.Item>
            )}
          </Stack>
        </div>
      )}
      {showCopyUrl && <ConfirmCopyUrlToClipboard onDismiss={() => setShowCopyUrl(false)} resource={props.resource} />}
    </>
  );
};

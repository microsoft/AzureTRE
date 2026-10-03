import React, { useCallback, useContext, useState, useEffect } from "react";
import { ComponentAction, VMPowerStates, Resource } from "../../models/resource";
import {
  Callout,
  DefaultPalette,
  FontWeights,
  IconButton,
  IStackStyles,
  IStyle,
  mergeStyleSets,
  PrimaryButton,
  Shimmer,
  Stack,
  Text,
  TooltipHost,
} from "@fluentui/react";
import { useNavigate } from "react-router-dom";
import moment from "moment";
import { ResourceContextMenu } from "./ResourceContextMenu";
import { useComponentManager } from "../../hooks/useComponentManager";
import { StatusBadge } from "./StatusBadge";
import { actionsDisabledStates, successStates } from "../../models/operation";
import { PowerStateBadge } from "./PowerStateBadge";
import { ResourceType } from "../../models/resourceType";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { CostsTag } from "./CostsTag";
import { ConfirmCopyUrlToClipboard } from "./ConfirmCopyUrlToClipboard";
import { AppRolesContext } from "../../contexts/AppRolesContext";
import { SecuredByRole } from "./SecuredByRole";
import { RoleName, WorkspaceRoleName } from "../../models/roleNames";
import { UserResource } from "../../models/userResource";
import { CachedUser } from "../../models/user";
import { useAccount, useMsal } from "@azure/msal-react";
import { VMPowerButton } from "./VMPowerButton";
import { openExternalUrl } from "../../utils/openExternalUrl";

interface ResourceCardProps {
  resource: Resource;
  itemId: number;
  selectResource?: (resource: Resource) => void;
  onUpdate: (resource: Resource) => void;
  onDelete: (resource: Resource) => void;
  readonly?: boolean;
  isExposedExternally?: boolean;
  usersCache?: Map<string, CachedUser>; // ownerId -> user info mapping
}

export const ResourceCard: React.FunctionComponent<ResourceCardProps> = (props: ResourceCardProps) => {
  const [loading] = useState(false);
  const [showCopyUrl, setShowCopyUrl] = useState(false);
  const [showInfo, setShowInfo] = useState(false);
  const workspaceCtx = useContext(WorkspaceContext);
  const latestUpdate = useComponentManager(
    props.resource,
    (r: Resource) => {
      props.onUpdate(r);
    },
    (r: Resource) => {
      props.onDelete(r);
    },
  );
  const navigate = useNavigate();

  const { accounts } = useMsal();
  const account = useAccount(accounts[0] || {});
  const currentUserId =
    (account?.idTokenClaims as Record<string, unknown> | undefined)?.oid?.toString() ||
    account?.localAccountId.split(".")[0] ||
    "";

  // The workspace users list is only available to Workspace Owners, so fall back to the signed-in user's own details.
  const getOwner = useCallback((): CachedUser | undefined => {
    if (props.resource.resourceType !== ResourceType.UserResource) return undefined;
    const ownerId = (props.resource as UserResource).ownerId;
    if (!ownerId || !ownerId.trim()) return undefined;
    const cached = props.usersCache?.get(ownerId);
    if (cached) return cached;
    if (ownerId === currentUserId && account?.name) return { displayName: account.name, email: account.username };
    return { displayName: ownerId } as CachedUser;
  }, [props.resource, props.usersCache, currentUserId, account]);

  // Get owner display name from cache or fallback to ownerId
  const getOwnerDisplayName = useCallback(() => getOwner()?.displayName || null, [getOwner]);

  // Get owner email from cache
  const getOwnerEmail = useCallback(() => getOwner()?.email || null, [getOwner]);

  const costTagRolesByResourceType = {
    [ResourceType.Workspace]: [RoleName.TREAdmin, WorkspaceRoleName.WorkspaceOwner],
    [ResourceType.SharedService]: [RoleName.TREAdmin],
    [ResourceType.WorkspaceService]: [WorkspaceRoleName.WorkspaceOwner],
    [ResourceType.UserResource]: [WorkspaceRoleName.WorkspaceOwner], // when implemented WorkspaceRoleName.WorkspaceResearcher]
  };

  const costsTagsRoles = costTagRolesByResourceType[props.resource.resourceType];

  const goToResource = useCallback(() => {
    const { resource } = props;
    const { resourceType, resourcePath, id } = resource;

    // shared services are accessed from the root and the workspace, have to handle the URL differently
    const resourceUrl = ResourceType.SharedService === resourceType && workspaceCtx.workspace.id ? id : resourcePath;

    props.selectResource?.(resource);
    navigate(resourceUrl);
  }, [navigate, props, workspaceCtx.workspace]);

  let connectUri = props.resource.properties && props.resource.properties.connection_uri;
  // Same precedence as the resource header and context menu: the resource's own setting wins.
  const isExposedExternally = props.resource.properties?.is_exposed_externally ?? props.isExposedExternally ?? true;
  const shouldDisable = () => {
    return (
      latestUpdate.componentAction === ComponentAction.Lock ||
      actionsDisabledStates.includes(props.resource.deploymentStatus) ||
      !props.resource.isEnabled ||
      (props.resource.azureStatus?.powerState && props.resource.azureStatus.powerState !== VMPowerStates.Running)
    );
  };

  const resourceStatus = latestUpdate.operation?.status
    ? latestUpdate.operation.status
    : props.resource.deploymentStatus;

  // Decide what to show as the top-right header badge
  let headerBadge = <></>;
  if (
    latestUpdate.componentAction !== ComponentAction.Lock &&
    props.resource.azureStatus?.powerState &&
    successStates.includes(resourceStatus) &&
    props.resource.isEnabled
  ) {
    headerBadge = <PowerStateBadge state={props.resource.azureStatus.powerState} />;
  } else {
    headerBadge = <StatusBadge resource={props.resource} status={resourceStatus} />;
  }

  const appRoles = useContext(AppRolesContext);
  const authNotProvisioned =
    props.resource.resourceType === ResourceType.Workspace && !props.resource.properties.scope_id;
  const enableClickOnCard = !authNotProvisioned || appRoles.roles.includes(RoleName.TREAdmin);
  const workspaceId = props.resource.resourceType === ResourceType.Workspace ? props.resource.id : "";
  const cardStyles = enableClickOnCard ? noNavCardStyles : clickableCardStyles;

  return (
    <>
      {loading ? (
        <Stack styles={noNavCardStyles}>
          <Stack.Item style={headerStyles}>
            <Shimmer width="70%" />
          </Stack.Item>
          <Stack.Item grow={3} style={bodyStyles}>
            <br />
            <Shimmer />
            <br />
            <Shimmer />
          </Stack.Item>
          <Stack.Item style={footerStyles}>
            <Shimmer />
          </Stack.Item>
        </Stack>
      ) : (
        <TooltipHost
          content={authNotProvisioned ? "Authentication has not yet been provisioned for this resource." : ""}
          id={`card-${props.resource.id}`}
          styles={{ root: { width: "100%" } }}
        >
          <Stack
            styles={cardStyles}
            aria-labelledby={`card-${props.resource.id}`}
            onClick={() => {
              if (enableClickOnCard) goToResource();
            }}
          >
            <Stack horizontal>
              <Stack.Item grow={5} style={headerStyles}>
                {props.resource.properties.display_name}
              </Stack.Item>

              {headerBadge}
            </Stack>
            {props.resource.resourceType === ResourceType.UserResource && getOwnerDisplayName() && (
              <Stack>
                <Stack.Item grow={3} style={userResourceOwner}>
                  <Text variant="small" style={{ color: DefaultPalette.neutralSecondary, marginTop: 5 }}>
                    {getOwnerDisplayName()}
                  </Text>
                </Stack.Item>
              </Stack>
            )}
            <Stack.Item grow={3} style={bodyStyles}>
              <Text>{props.resource.properties.description}</Text>
            </Stack.Item>

            <Stack horizontal style={footerStyles}>
              <Stack.Item grow>
                <Stack horizontal>
                  <Stack.Item>
                    <IconButton
                      iconProps={{ iconName: "Info" }}
                      ariaLabel="Resource details"
                      title="Resource details"
                      id={`item-${props.itemId}`}
                      onClick={(e) => {
                        // Stop onClick triggering parent handler
                        e.stopPropagation();
                        setShowInfo(!showInfo);
                      }}
                    />
                  </Stack.Item>
                  <Stack.Item>
                    {!props.readonly && (
                      <ResourceContextMenu
                        resource={props.resource}
                        componentAction={latestUpdate.componentAction}
                        isExposedExternally={props.isExposedExternally}
                      />
                    )}
                  </Stack.Item>
                  {!props.readonly && (
                    <Stack.Item>
                      <VMPowerButton
                        resource={props.resource}
                        componentAction={latestUpdate.componentAction}
                        iconOnly
                      />
                    </Stack.Item>
                  )}
                </Stack>
              </Stack.Item>
              <SecuredByRole
                allowedAppRoles={costsTagsRoles}
                allowedWorkspaceRoles={costsTagsRoles}
                workspaceId={workspaceId}
                element={<CostsTag resourceId={props.resource.id} resourceType={props.resource.resourceType} />}
              />
              {connectUri && (
                <PrimaryButton
                  onClick={(e) => {
                    e.stopPropagation();
                    isExposedExternally ? openExternalUrl(connectUri) : setShowCopyUrl(true);
                  }}
                  disabled={shouldDisable()}
                  title={
                    shouldDisable()
                      ? "Resource must be enabled, successfully deployed & powered on to connect"
                      : "Connect to resource"
                  }
                  className={styles.button}
                >
                  Connect
                </PrimaryButton>
              )}
              {showCopyUrl && (
                <ConfirmCopyUrlToClipboard onDismiss={() => setShowCopyUrl(false)} resource={props.resource} />
              )}
            </Stack>
          </Stack>
        </TooltipHost>
      )}
      {showInfo && (
        <Callout
          className={styles.callout}
          ariaLabelledBy={`item-${props.itemId}-label`}
          ariaDescribedBy={`item-${props.itemId}-description`}
          role="dialog"
          gapSpace={0}
          target={`#item-${props.itemId}`}
          onDismiss={() => {
            setShowInfo(false);
          }}
          setInitialFocus
        >
          <Text block variant="xLarge" className={styles.title} id={`item-${props.itemId}-label`}>
            {props.resource.templateName} ({props.resource.templateVersion})
          </Text>
          <Text block variant="small" id={`item-${props.itemId}-description`}>
            <Stack>
              <Stack.Item>
                <Stack horizontal tokens={{ childrenGap: 5 }}>
                  <Stack.Item style={calloutKeyStyles}>Resource Id:</Stack.Item>
                  <Stack.Item style={calloutValueStyles}>{props.resource.id}</Stack.Item>
                </Stack>
                <Stack horizontal tokens={{ childrenGap: 5 }}>
                  <Stack.Item style={calloutKeyStyles}>Last Modified By:</Stack.Item>
                  <Stack.Item style={calloutValueStyles}>{props.resource.user.name}</Stack.Item>
                </Stack>
                {props.resource.resourceType === ResourceType.UserResource &&
                  (props.resource as UserResource).ownerId &&
                  (props.resource as UserResource).ownerId.trim() && (
                    <>
                      <Stack horizontal tokens={{ childrenGap: 5 }}>
                        <Stack.Item style={calloutKeyStyles}>Owner ID:</Stack.Item>
                        <Stack.Item style={calloutValueStyles}>{(props.resource as UserResource).ownerId}</Stack.Item>
                      </Stack>
                      {getOwnerDisplayName() && (
                        <Stack horizontal tokens={{ childrenGap: 5 }}>
                          <Stack.Item style={calloutKeyStyles}>Owner:</Stack.Item>
                          <Stack.Item style={calloutValueStyles}>
                            {getOwnerDisplayName()}
                            {getOwnerEmail() && (
                              <>
                                {" "}
                                <a
                                  href={`mailto:${getOwnerEmail()}`}
                                  style={{ color: DefaultPalette.themePrimary, textDecoration: "none" }}
                                >
                                  ({getOwnerEmail()})
                                </a>
                              </>
                            )}
                          </Stack.Item>
                        </Stack>
                      )}
                    </>
                  )}
                <Stack horizontal tokens={{ childrenGap: 5 }}>
                  <Stack.Item style={calloutKeyStyles}>Last Updated:</Stack.Item>
                  <Stack.Item style={calloutValueStyles}>
                    {moment.unix(props.resource.updatedWhen).toDate().toDateString()}
                  </Stack.Item>
                </Stack>
              </Stack.Item>
            </Stack>
          </Text>
        </Callout>
      )}
    </>
  );
};

const baseCardStyles: IStyle = {
  width: "100%",
  borderRadius: "5px",
  boxShadow: "0 1.6px 3.6px 0 rgba(0,0,0,.132),0 .3px .9px 0 rgba(0,0,0,.108)",
  backgroundColor: DefaultPalette.white,
  padding: 10,
};

const noNavCardStyles: IStackStyles = {
  root: { ...baseCardStyles },
};

const clickableCardStyles: IStackStyles = {
  root: {
    ...baseCardStyles,
    "&:hover": {
      transition: "all .2s ease-in-out",
      transform: "scale(1.02)",
      cursor: "pointer",
    },
  },
};

const headerStyles: React.CSSProperties = {
  padding: "5px 10px",
  fontSize: "1.2rem",
};

const bodyStyles: React.CSSProperties = {
  padding: "10px 10px",
  minHeight: "40px",
};

const userResourceOwner: React.CSSProperties = {
  padding: "0px 10px",
  minHeight: "40px",
};

const footerStyles: React.CSSProperties = {
  minHeight: "30px",
  alignItems: "center",
};

const calloutKeyStyles: React.CSSProperties = {
  width: 160,
};

const calloutValueStyles: React.CSSProperties = {
  maxWidth: 400,
};

const styles = mergeStyleSets({
  button: {
    width: 130,
    margin: 10,
  },
  callout: {
    padding: "20px 24px",
    maxWidth: 600,
    minWidth: 220,
  },
  title: {
    marginBottom: 12,
    fontWeight: FontWeights.semilight,
  },
  link: {
    display: "block",
    marginTop: 20,
  },
});

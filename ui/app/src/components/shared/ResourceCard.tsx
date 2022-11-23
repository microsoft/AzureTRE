import React, { useCallback, useContext, useState } from 'react';
import { ComponentAction, VMPowerStates, Resource } from '../../models/resource';
import { Callout, DefaultPalette, FontWeights, IconButton, IStackStyles, IStyle, mergeStyleSets, PrimaryButton, Shimmer, Stack, Text, TooltipHost } from '@fluentui/react';
import { useNavigate } from 'react-router-dom';
import moment from 'moment';
import { ResourceContextMenu } from './ResourceContextMenu';
import { useComponentManager } from '../../hooks/useComponentManager';
import { StatusBadge } from './StatusBadge';
import { actionsDisabledStates, successStates } from '../../models/operation';
import { PowerStateBadge } from './PowerStateBadge';
import { ResourceType } from '../../models/resourceType';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import { CostsTag } from './CostsTag';

interface ResourceCardProps {
  resource: Resource,
  itemId: number,
  selectResource?: (resource: Resource) => void,
  onUpdate: (resource: Resource) => void,
  onDelete: (resource: Resource) => void,
  readonly?: boolean
}

export const ResourceCard: React.FunctionComponent<ResourceCardProps> = (props: ResourceCardProps) => {
  const [loading] = useState(false);
  const [showInfo, setShowInfo] = useState(false);
  const workspaceCtx = useContext(WorkspaceContext);
  const latestUpdate = useComponentManager(
    props.resource,
    (r: Resource) => { props.onUpdate(r) },
    (r: Resource) => { props.onDelete(r) }
  );
  const navigate = useNavigate();

  const goToResource = useCallback(() => {
    let resourceUrl = '';
    switch(props.resource.resourceType) {
      case ResourceType.Workspace:
      case ResourceType.WorkspaceService:
      case ResourceType.UserResource:
        resourceUrl = props.resource.resourcePath;
        break;
      case ResourceType.SharedService: // shared services are accessed from the root and the workspace, have to handle the URL differently
        resourceUrl = workspaceCtx.workspace ? props.resource.id : props.resource.resourcePath;
        break;
    }

    props.selectResource && props.selectResource(props.resource);
    navigate(resourceUrl);
  }, [navigate, props, workspaceCtx.workspace]);

  let connectUri = props.resource.properties && props.resource.properties.connection_uri;
  const shouldDisable = () => {
    return latestUpdate.componentAction === ComponentAction.Lock
      || actionsDisabledStates.includes(props.resource.deploymentStatus)
      || !props.resource.isEnabled
      || (props.resource.azureStatus?.powerState && props.resource.azureStatus.powerState !== VMPowerStates.Running)
  }

  const resourceStatus = latestUpdate.operation?.status
    ? latestUpdate.operation.status
    : props.resource.deploymentStatus

  // Decide what to show as the top-right header badge
  let headerBadge = <></>;
  if (
    latestUpdate.componentAction !== ComponentAction.Lock &&
    props.resource.azureStatus?.powerState &&
    successStates.includes(resourceStatus) &&
    props.resource.isEnabled
  ) {
    headerBadge = <PowerStateBadge state={props.resource.azureStatus.powerState} />
  } else {
    headerBadge = <StatusBadge resource={props.resource} status={resourceStatus} />
  }

  const authNotProvisioned = props.resource.resourceType === ResourceType.Workspace && !props.resource.properties.scope_id;
  const cardStyles = authNotProvisioned ? noNavCardStyles : clickableCardStyles;

  return (
    <>
      {
        loading ? <Stack styles={noNavCardStyles}>
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
        </Stack> : <TooltipHost
          content={authNotProvisioned ? "Authentication has not yet been provisioned for this resource." : ""}
          id={`card-${props.resource.id}`}
          styles={{root: {width:'100%'}}}
        >
          <Stack
            styles={cardStyles}
            aria-labelledby={`card-${props.resource.id}`}
            onClick={() => {if (!authNotProvisioned) goToResource()}}
          >
            <Stack horizontal>
              <Stack.Item grow={5} style={headerStyles}>{props.resource.properties.display_name}</Stack.Item>
              {headerBadge}
            </Stack>

            <Stack.Item grow={3} style={bodyStyles}>
              <Text>{props.resource.properties.description}</Text>
            </Stack.Item>

            <Stack horizontal style={footerStyles}>
              <Stack.Item grow>
                <Stack horizontal>
                  <Stack.Item>
                    <IconButton
                      iconProps={{iconName: 'Info'}}
                      id={`item-${props.itemId}`}
                      onClick={(e) => {
                        // Stop onClick triggering parent handler
                        e.stopPropagation();
                        setShowInfo(!showInfo);
                      }}
                    />
                  </Stack.Item>
                  <Stack.Item>
                    {
                      !props.readonly && <ResourceContextMenu
                        resource={props.resource}
                        componentAction={latestUpdate.componentAction}
                      />
                    }
                  </Stack.Item>
                </Stack>
              </Stack.Item>
              <CostsTag resourceId={props.resource.id} />
              {
                connectUri && <PrimaryButton
                  onClick={(e) => {e.stopPropagation(); window.open(connectUri)}}
                  disabled={shouldDisable()}
                  title={shouldDisable() ? 'Resource must be enabled, successfully deployed & powered on to connect' : 'Connect to resource'}>
                  Connect
                </PrimaryButton>
              }
            </Stack>
          </Stack>
        </TooltipHost>
      }
      {
        showInfo && <Callout
          className={styles.callout}
          ariaLabelledBy={`item-${props.itemId}-label`}
          ariaDescribedBy={`item-${props.itemId}-description`}
          role="dialog"
          gapSpace={0}
          target={`#item-${props.itemId}`}
          onDismiss={() => setShowInfo(false)}
          setInitialFocus
        >
          <Text block variant="xLarge" className={styles.title} id={`item-${props.itemId}-label`}>
            {props.resource.templateName} ({props.resource.templateVersion})
          </Text>
          <Text block variant="small" id={`item-${props.itemId}-description`}>
            <Stack>
              <Stack.Item>
                <Stack horizontal tokens={{childrenGap: 5}}>
                  <Stack.Item style={calloutKeyStyles}>Resource Id:</Stack.Item>
                  <Stack.Item style={calloutValueStyles}>{props.resource.id}</Stack.Item>
                </Stack>
                <Stack horizontal tokens={{childrenGap: 5}}>
                  <Stack.Item style={calloutKeyStyles}>Last Modified By:</Stack.Item>
                  <Stack.Item style={calloutValueStyles}>{props.resource.user.name}</Stack.Item>
                </Stack>
                <Stack horizontal tokens={{childrenGap: 5}}>
                  <Stack.Item style={calloutKeyStyles}>Last Updated:</Stack.Item>
                  <Stack.Item style={calloutValueStyles}>{moment.unix(props.resource.updatedWhen).toDate().toDateString()}</Stack.Item>
                </Stack>
              </Stack.Item>
            </Stack>
          </Text>
        </Callout>
      }
    </>
  )
};

const baseCardStyles: IStyle = {
  width: '100%',
  borderRadius: '5px',
  boxShadow: '0 1.6px 3.6px 0 rgba(0,0,0,.132),0 .3px .9px 0 rgba(0,0,0,.108)',
  backgroundColor: DefaultPalette.white,
  padding: 10
}

const noNavCardStyles: IStackStyles = {
  root: { ...baseCardStyles }
}

const clickableCardStyles: IStackStyles = {
  root: {
    ...baseCardStyles,
    "&:hover": {
      transition: 'all .2s ease-in-out',
      transform: 'scale(1.02)',
      cursor: 'pointer'
    }
  }
}

const headerStyles: React.CSSProperties = {
  padding: '5px 10px',
  fontSize: '1.2rem',
};

const bodyStyles: React.CSSProperties = {
  padding: '10px 10px',
  minHeight: '40px'
}

const footerStyles: React.CSSProperties = {
  minHeight: '30px',
  alignItems: 'center'
}

const calloutKeyStyles: React.CSSProperties = {
  width: 160
}

const calloutValueStyles: React.CSSProperties = {
  width: 180
}

const styles = mergeStyleSets({
  button: {
    width: 130,
  },
  callout: {
    width: 350,
    padding: '20px 24px',
  },
  title: {
    marginBottom: 12,
    fontWeight: FontWeights.semilight
  },
  link: {
    display: 'block',
    marginTop: 20,
  }
});

import React, { useState } from 'react';
import { ComponentAction, VMPowerStates, Resource } from '../../models/resource';
import { Callout, DefaultPalette, FontWeights, IconButton, mergeStyleSets, PrimaryButton, ProgressIndicator, Shimmer, Stack, Text } from '@fluentui/react';
import { Link } from 'react-router-dom';
import moment from 'moment';
import { ResourceContextMenu } from './ResourceContextMenu';
import { useComponentManager } from '../../hooks/useComponentManager';
import { StatusBadge } from './StatusBadge';
import { actionsDisabledStates } from '../../models/operation';
import { PowerStateBadge } from './PowerStateBadge';
import { ResourceType } from '../../models/resourceType';

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
  const latestUpdate = useComponentManager(
    props.resource,
    (r: Resource) => { props.onUpdate(r) },
    (r: Resource) => { props.onDelete(r) }
  );

  let connectUri = props.resource.properties && props.resource.properties.connection_uri;
  const shouldDisable = () => {
    return latestUpdate.componentAction === ComponentAction.Lock
      || actionsDisabledStates.includes(props.resource.deploymentStatus)
      || !props.resource.isEnabled
      || (props.resource.azureStatus?.powerState && props.resource.azureStatus.powerState !== VMPowerStates.Running)
  }

  return (
    <>
      {
        loading ?
          <>
            <Stack style={cardStyles}>
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
          </> :
          <Stack style={cardStyles}>
            <Stack horizontal>
              <Stack.Item grow={5} style={headerStyles}>
                {
                  props.resource.resourceType === ResourceType.Workspace && props.resource.properties.client_id === "auto_create" ?
                    <span title="Authentication has not yet been provisioned">{props.resource.properties.display_name}</span>
                    :
                    <Link to={props.resource.resourceType === ResourceType.Workspace ? props.resource.resourcePath : props.resource.id} onClick={() => { props.selectResource && props.selectResource(props.resource); return false }} style={headerLinkStyles}>{props.resource.properties.display_name}</Link>
                }
              </Stack.Item>
              <Stack.Item style={headerIconStyles}>
                <Stack horizontal>
                  <Stack.Item>
                    <IconButton iconProps={{ iconName: 'Info' }} id={`item-${props.itemId}`} onClick={() => setShowInfo(!showInfo)} /></Stack.Item>
                  <Stack.Item>
                    {
                      !props.readonly &&
                      <ResourceContextMenu
                        resource={props.resource}
                        componentAction={latestUpdate.componentAction} />
                    }
                  </Stack.Item>
                </Stack>
              </Stack.Item>
            </Stack>
            <Stack.Item grow={3} style={bodyStyles}>
              <Text>{props.resource.properties.description}</Text>
            </Stack.Item>
            {
              connectUri &&
              <Stack.Item style={connectStyles}>
                <PrimaryButton
                  onClick={() => window.open(connectUri)}
                  disabled={shouldDisable()}
                  title={shouldDisable() ? 'Resource must be enabled, successfully deployed & powered on to connect' : 'Connect to resource'}>
                  Connect
                </PrimaryButton>
              </Stack.Item>
            }
            <Stack.Item style={footerStyles}>
              <Stack horizontal>
                <Stack.Item grow={1} align="center">
                  {
                    latestUpdate.componentAction === ComponentAction.Lock &&
                    <ProgressIndicator
                      barHeight={4}
                      description='Resource is locked for changes whilst it updates.' />
                  }
                  {
                    (props.resource.azureStatus?.powerState && latestUpdate.componentAction !== ComponentAction.Lock) &&
                    <div style={{ marginTop: 5 }}>
                      <PowerStateBadge state={props.resource.azureStatus.powerState} />
                    </div>
                  }
                </Stack.Item>
                <Stack.Item style={{ paddingTop: 2, paddingLeft: 10 }}>
                  <StatusBadge resourceId={props.resource.id} status={latestUpdate.operation ? latestUpdate.operation?.status : props.resource.deploymentStatus} />
                </Stack.Item>
              </Stack>
            </Stack.Item>
          </Stack>
      }
      {
        showInfo &&
        <Callout
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
            {props.resource.templateName} - ({props.resource.templateVersion})
          </Text>
          <Text block variant="small" id={`item-${props.itemId}-description`}>
            <Stack>
              <Stack.Item>
                <Stack horizontal tokens={{ childrenGap: 5 }}>
                  <Stack.Item style={calloutKeyStyles}>Last Modified By:</Stack.Item>
                  <Stack.Item style={calloutValueStyles}>{props.resource.user.name}</Stack.Item>
                </Stack>
                <Stack horizontal tokens={{ childrenGap: 5 }}>
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

const cardStyles: React.CSSProperties = {
  width: '100%',
  borderRadius: '2px',
  border: '1px #ccc solid',
  //  boxShadow: '1px 0px 4px 0px #dddddd'
}

const headerStyles: React.CSSProperties = {
  padding: '5px 10px',
  fontSize: '1.3rem',
};

const headerIconStyles: React.CSSProperties = {
  padding: '5px'
}

const headerLinkStyles: React.CSSProperties = {
  color: DefaultPalette.themePrimary,
  textDecoration: 'none'
}

const bodyStyles: React.CSSProperties = {
  padding: '5px 10px',
  minHeight: '40px'
}

const connectStyles: React.CSSProperties = {
  padding: '5px 10px'
}

const footerStyles: React.CSSProperties = {
  backgroundColor: DefaultPalette.white,
  padding: '5px 7px',
  minHeight: '30px',
  borderTop: '1px #ccc solid',
}

const calloutKeyStyles: React.CSSProperties = {
  width: 120
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

import React, { useContext, useEffect, useRef, useState } from 'react';
import { ComponentAction, getResourceFromResult, Resource, ResourceUpdate } from '../../models/resource';
import { Callout, DefaultPalette, FontWeights, IconButton, mergeStyleSets, PrimaryButton, ProgressIndicator, Shimmer, Stack, Text } from '@fluentui/react';
import { Link } from 'react-router-dom';
import moment from 'moment';
import { NotificationsContext } from '../../contexts/NotificationsContext';
import { HttpMethod, useAuthApiCall } from '../../useAuthApiCall';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import { ResourceContextMenu } from './ResourceContextMenu';

interface ResourceCardProps {
  resource: Resource,
  itemId: number,
  selectResource?: (resource: Resource) => void,
  onUpdate: (resource: Resource) => void,
  onDelete: (resource: Resource) => void
}

export const ResourceCard: React.FunctionComponent<ResourceCardProps> = (props: ResourceCardProps) => {
  const apiCall = useAuthApiCall();
  const workspaceCtx = useContext(WorkspaceContext);
  const [loading, setLoading] = useState(false);
  const [showInfo, setShowInfo] = useState(false);
  const [componentAction, setComponentAction] = useState(ComponentAction.None);

  const opsReadContext = useContext(NotificationsContext);
  const opsWriteContext = useRef(useContext(NotificationsContext)); // useRef to avoid re-running a hook on context write

  // set the latest component action
  useEffect(() => {
    let updates = opsReadContext.resourceUpdates.filter((r: ResourceUpdate) => { return r.resourceId === props.resource.id });
    setComponentAction((updates && updates.length > 0) ?
      updates[updates.length - 1].componentAction :
      ComponentAction.None);
  }, [opsReadContext.resourceUpdates, props.resource.id])

  // act on component action changes
  useEffect(() => {
    const checkForReload = async () => {
      if (componentAction === ComponentAction.Reload) {
        setLoading(true);
        let result = await apiCall(props.resource.resourcePath, HttpMethod.Get, workspaceCtx.workspaceClientId);
        let r = getResourceFromResult(result);
        setLoading(false);
        opsWriteContext.current.clearUpdatesForResource(props.resource.id);
        props.onUpdate(r);
      } else if (componentAction === ComponentAction.Remove) {
        opsWriteContext.current.clearUpdatesForResource(props.resource.id);
        props.onDelete(props.resource);
      }
    }
    checkForReload();
  }, [apiCall, componentAction, props, workspaceCtx.workspaceClientId]);

  let connectUri = props.resource.properties && props.resource.properties.connection_uri;

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
                <Link to={props.resource.resourcePath} onClick={() => { props.selectResource && props.selectResource(props.resource); return false }} style={headerLinkStyles}>{props.resource.properties.display_name}</Link>
              </Stack.Item>
              <Stack.Item style={headerIconStyles}>
                <Stack horizontal>
                  <Stack.Item>
                    <IconButton iconProps={{ iconName: 'Info' }} id={`item-${props.itemId}`} onClick={() => setShowInfo(!showInfo)} /></Stack.Item>
                  <Stack.Item>
                    <ResourceContextMenu
                      resource={props.resource} />
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
                <PrimaryButton onClick={() => window.open(connectUri)} disabled={!props.resource.isEnabled} title={!props.resource.isEnabled ? 'Enable resource to connect' : 'Connect to resource'}>Connect</PrimaryButton>
              </Stack.Item>
            }
            <Stack.Item style={footerStyles}>
              {
                componentAction === ComponentAction.Lock &&
                <ProgressIndicator
                  barHeight={4}
                  description='Resource is locked for changes whilst it updates.' />
              }
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
  border: '1px #ccc solid'
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
  padding: '5px 10px',
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

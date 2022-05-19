import React, { useContext, useEffect, useRef, useState } from 'react';
import { ComponentAction, getResourceFromResult, Resource, ResourceUpdate } from '../../models/resource';
import { Callout, DefaultPalette, FontWeights, IconButton, IContextualMenuItem, IContextualMenuProps, mergeStyleSets, ProgressIndicator, Shimmer, ShimmerElementType, Stack, Text } from '@fluentui/react';
import { Link } from 'react-router-dom';
import moment from 'moment';
import { RoleName } from '../../models/roleNames';
import { SecuredByRole } from './SecuredByRole';
import { ResourceType } from '../../models/resourceType';
import { ConfirmDisableEnableResource } from './ConfirmDisableEnableResource';
import { NotificationsContext } from '../../contexts/NotificationsContext';
import { HttpMethod, useAuthApiCall } from '../../useAuthApiCall';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';

interface ResourceCardProps {
  resource: Resource,
  itemId: number,
  selectResource: (resource: Resource) => void
}

export const ResourceCard: React.FunctionComponent<ResourceCardProps> = (props: ResourceCardProps) => {
  const apiCall = useAuthApiCall();
  const workspaceCtx = useContext(WorkspaceContext);
  const [resource, setResource] = useState(props.resource);
  const [loading, setLoading] = useState(false);
  const [showInfo, setShowInfo] = useState(false);
  const [showDisable, setShowDisable] = useState(false);
  const [componentAction, setComponentAction] = useState(ComponentAction.None);

  const opsReadContext = useContext(NotificationsContext);
  const opsWriteContext = useRef(useContext(NotificationsContext)); // useRef to avoid re-running a hook on context write

  // set the latest component action
  useEffect(() => {
    let updates = opsReadContext.resourceUpdates.filter((r: ResourceUpdate) => { return r.resourceId === resource.id });
    setComponentAction((updates && updates.length > 0) ?
      updates[updates.length - 1].componentAction :
      ComponentAction.None);
  }, [opsReadContext.resourceUpdates, resource.id])

  // act on component action changes
  useEffect(() => {
    const checkForReload = async () => {
      if (componentAction === ComponentAction.Reload) {
        setLoading(true);
        let r = await apiCall(resource.resourcePath, HttpMethod.Get, workspaceCtx.workspaceClientId);
        setResource(getResourceFromResult(r));
        setLoading(false);
        opsWriteContext.current.clearUpdatesForResource(resource.id);
      }
    }
    checkForReload();
  }, [apiCall, componentAction, resource.id, resource.resourcePath, workspaceCtx.workspaceClientId]);

  // context menu
  let i: Array<IContextualMenuItem> = [];
  let roles: Array<string> = [];
  switch (resource.resourceType) {
    case ResourceType.Workspace:
      i = [
        { key: 'update', text: 'Update', iconProps: { iconName: 'WindowEdit' }, onClick: () => console.log('update') },
        { key: 'disable', text: resource.isEnabled ? 'Disable' : 'Enable', iconProps: { iconName: resource.isEnabled ? 'CirclePause' : 'PlayResume' }, onClick: () => setShowDisable(true) },
        { key: 'delete', text: 'Delete', iconProps: { iconName: 'Delete' }, onClick: () => console.log('delete clicked') }
      ];
      roles = [RoleName.TREAdmin];
      break;
  }

  const menuProps: IContextualMenuProps = {
    shouldFocusOnMount: true,
    items: i,
  };

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
                <Link to={resource.resourcePath} onClick={() => { props.selectResource(resource); return false }} style={headerLinkStyles}>{resource.properties.display_name}</Link>
              </Stack.Item>
              <Stack.Item style={headerIconStyles}>
                <Stack horizontal>
                  <Stack.Item><IconButton iconProps={{ iconName: 'Info' }} id={`item-${props.itemId}`} onClick={() => setShowInfo(!showInfo)} /></Stack.Item>
                  <Stack.Item>
                    <SecuredByRole allowedRoles={roles} element={
                      <IconButton iconProps={{ iconName: 'More' }} menuProps={menuProps} className="tre-hide-chevron" disabled={componentAction === ComponentAction.Lock} />
                    } />
                  </Stack.Item>
                </Stack>
              </Stack.Item>
            </Stack>
            <Stack.Item grow={3} style={bodyStyles}>
              <Text>{resource.properties.description}</Text>
            </Stack.Item>
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
        showDisable &&
        <ConfirmDisableEnableResource onDismiss={() => setShowDisable(false)} resource={resource} isEnabled={!resource.isEnabled} />
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
            {resource.templateName} - ({resource.templateVersion})
          </Text>
          <Text block variant="small" id={`item-${props.itemId}-description`}>
            <Stack>
              <Stack.Item>
                <Stack horizontal tokens={{ childrenGap: 5 }}>
                  <Stack.Item style={calloutKeyStyles}>Last Modified By:</Stack.Item>
                  <Stack.Item style={calloutValueStyles}>{resource.user.name}</Stack.Item>
                </Stack>
                <Stack horizontal tokens={{ childrenGap: 5 }}>
                  <Stack.Item style={calloutKeyStyles}>Last Updated:</Stack.Item>
                  <Stack.Item style={calloutValueStyles}>{moment.unix(resource.updatedWhen).toDate().toDateString()}</Stack.Item>
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
  borderBottom: '1px #ccc solid',
  padding: '5px 10px',
  minHeight: '70px'
}

const footerStyles: React.CSSProperties = {
  backgroundColor: DefaultPalette.white,
  padding: '5px 10px',
  minHeight: '30px'
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
    fontWeight: FontWeights.semilight,
  },
  link: {
    display: 'block',
    marginTop: 20,
  },
});
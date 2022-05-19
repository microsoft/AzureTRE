import React, { useState } from 'react';
import { Resource } from '../../models/resource';
import { Callout, DefaultPalette, FontWeights, IconButton, mergeStyleSets, PrimaryButton, Stack, Text } from '@fluentui/react';
import { Link } from 'react-router-dom';
import moment from 'moment';

interface ResourceCardProps {
  resource: Resource,
  itemId: number,
  selectResource: (resource: Resource) => void,
  contextMenuElement?: JSX.Element
}

export const ResourceCard: React.FunctionComponent<ResourceCardProps> = (props: ResourceCardProps) => {
  const [showInfo, setShowInfo] = useState(false);

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
    minHeight: '70px'
  }

  const bodyStylesWithConnect: React.CSSProperties = {
    padding: '5px 10px',
    minHeight: '40px'
  }

  const connectStyles: React.CSSProperties = {
    padding: '5px 10px'
  }

  const footerStyles: React.CSSProperties = {
    backgroundColor: DefaultPalette.white,
    borderTop: '1px #ccc solid',
    padding: '5px 10px',
    minHeight: '30px'
  }

  const calloutKeyStyles: React.CSSProperties = {
    width: 100
  } 

  const calloutValueStyles: React.CSSProperties = {
    width: 200
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

  let connectUri = props.resource.properties && props.resource.properties['connection_uri'];

  return (
    <>
      <Stack style={cardStyles}>
        <Stack horizontal>
          <Stack.Item grow={5} style={headerStyles}>
            <Link to={props.resource.resourcePath} onClick={() => {props.selectResource(props.resource); return false}} style={headerLinkStyles}>{props.resource.properties.display_name}</Link>
          </Stack.Item>
          <Stack.Item style={headerIconStyles}>
            <Stack horizontal>
              <Stack.Item><IconButton iconProps={{iconName: 'Info'}} id={`item-${props.itemId}`} onClick={() => setShowInfo(!showInfo)} /></Stack.Item>
              <Stack.Item>{props.contextMenuElement && props.contextMenuElement}</Stack.Item>
            </Stack>
          </Stack.Item>
        </Stack>
        <Stack.Item grow={3} style={ (connectUri) ? bodyStylesWithConnect : bodyStyles}>
          <Text>{props.resource.properties.description}</Text>
        </Stack.Item>
        { 
        connectUri &&
        <Stack.Item style={connectStyles}>
            <PrimaryButton onClick={ () => window.open(connectUri) }>Connect</PrimaryButton>
        </Stack.Item>
        }
        <Stack.Item style={footerStyles}>
          &nbsp;
        </Stack.Item>
      </Stack>

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
               <Stack horizontal tokens={{childrenGap: 5}}>
                 <Stack.Item style={calloutKeyStyles}>Created By:</Stack.Item>
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


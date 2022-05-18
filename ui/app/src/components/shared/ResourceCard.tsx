import React from 'react';
import { Resource } from '../../models/resource';
import { DefaultPalette, Stack, Text } from '@fluentui/react';
import { Link } from 'react-router-dom';

interface ResourceCardProps {
  resource: Resource,
  to: string,
  selectResource: (resource: Resource) => void
}

export const ResourceCard: React.FunctionComponent<ResourceCardProps> = (props: ResourceCardProps) => {


  const cardStyles: React.CSSProperties = {
    width: '100%',
    borderRadius: '2px',
    border: '1px #ccc solid'
  }

  const headerStyles: React.CSSProperties = {
    padding: '5px 10px',
    fontSize: '1.3rem',

  };

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

  return (
    <>
      <Stack style={cardStyles}>
        <Stack.Item style={headerStyles}>
          <Link to={props.resource.resourcePath} onClick={() => {props.selectResource(props.resource); return false}} style={headerLinkStyles}>{props.resource.properties.display_name}</Link>
        </Stack.Item>
        <Stack.Item grow={3} style={bodyStyles}>
          <Text>{props.resource.properties.description}</Text>
        </Stack.Item>
        <Stack.Item style={footerStyles}>
          &nbsp;
        </Stack.Item>
      </Stack>
    </>
  )
};


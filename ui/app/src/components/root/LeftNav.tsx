import React from 'react';
import { Nav, INavLinkGroup } from '@fluentui/react/lib/Nav';
import { initializeIcons } from '@fluentui/react';
import { useNavigate } from 'react-router-dom';

const navLinkGroups: INavLinkGroup[] = [
  {
    links: [
      {
        name: 'Workspaces',
        url: '/',
        key: 'key1',
        icon: 'WebAppBuilderFragment'
      },
      {
        name: 'Settings',
        url: '/settings',
        key: 'key2',
        disabled: true,
        icon: 'Settings'
      },
      {
        name: 'Admin',
        url: '/admin',
        key: 'key3',
        disabled: false,
        icon: 'AdminALogoFill32'
      },
    ],
  },
];

initializeIcons()

export const LeftNav: React.FunctionComponent = () => {
  const navigate = useNavigate();

  return (
    <Nav
      onLinkClick={(e, item) => {e?.preventDefault(); item?.url && navigate(item.url)}}
      ariaLabel="TRE Left Navigation"
      groups={navLinkGroups}
    />
  );
};


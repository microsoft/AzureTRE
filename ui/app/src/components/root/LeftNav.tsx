import React from 'react';
import { Nav, INavLinkGroup } from '@fluentui/react/lib/Nav';
import { useNavigate } from 'react-router-dom';

const navLinkGroups: INavLinkGroup[] = [
  {
    links: [
      {
        name: 'Workspaces',
        url: '/',
        key: '/',
        icon: 'WebAppBuilderFragment'
      },
      {
        name: 'Shared Services',
        url: '/shared-services',
        key: 'shared-services',
        icon: 'Puzzle'
      },
      {
        name: 'Settings',
        url: '/settings',
        key: 'settings',
        disabled: true,
        icon: 'Settings'
      },
      {
        name: 'Admin',
        url: '/admin',
        key: 'admin',
        disabled: false,
        icon: 'AdminALogoFill32'
      },
    ],
  },
];

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


import React from 'react';
import { Nav, INavLinkGroup } from '@fluentui/react/lib/Nav';
import { initializeIcons } from '@fluentui/react';
import { useNavigate } from 'react-router-dom';

const navLinkGroups: INavLinkGroup[] = [
  {
    links: [
      {
        name: 'Services',
        key: 'services',
        url: '',
        isExpanded: true,
        links: [
          {
            name: 'Guacamole',
            url: 'workspace-services/1234456789',
            key: 'services-guacamole'
          },
          {
            name: 'ML Flow',
            url: 'workspace-services/987654321',
            key: 'services-mlflow'
          }
        ]
      }
    ]
  }
];

initializeIcons()

export const WorkspaceLeftNav: React.FunctionComponent = () => {
  const navigate = useNavigate();

  return (
    <Nav
      onLinkClick={(e, item) => { e?.preventDefault(); item?.url && navigate(item.url) }}
      ariaLabel="TRE Workspace Left Navigation"
      groups={navLinkGroups}
    />
  );
};


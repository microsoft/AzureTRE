import React, { useContext, useEffect, useState } from 'react';
import { Nav, INavLinkGroup, INavStyles } from '@fluentui/react/lib/Nav';
import { useNavigate } from 'react-router-dom';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { WorkspaceService } from '../../models/workspaceService';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import { SharedService } from '../../models/sharedService';

// TODO:
// - active item is sometimes lost

interface WorkspaceLeftNavProps {
  workspaceServices: Array<WorkspaceService>,
  sharedServices: Array<SharedService>,
  setWorkspaceService: (workspaceService: WorkspaceService) => void,
  addWorkspaceService: (w: WorkspaceService) => void
}

export const WorkspaceLeftNav: React.FunctionComponent<WorkspaceLeftNavProps> = (props: WorkspaceLeftNavProps) => {
  const navigate = useNavigate();
  const emptyLinks: INavLinkGroup[] = [{ links: [] }];
  const [serviceLinks, setServiceLinks] = useState(emptyLinks);
  const workspaceCtx = useContext(WorkspaceContext);

  useEffect(() => {
    const getWorkspaceServices = async () => {
      // get the workspace services
      if(!workspaceCtx.workspace.id) return;
      let serviceLinkArray: Array<any> = [];
      props.workspaceServices.forEach((service: WorkspaceService) => {
        serviceLinkArray.push(
          {
            name: service.properties.display_name,
            url: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.WorkspaceServices}/${service.id}`,
            key: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.WorkspaceServices}/${service.id}`
          });
      });

      let sharedServiceLinkArray: Array<any> = [];
      props.sharedServices.forEach((service: SharedService) => {
        sharedServiceLinkArray.push(
          {
            name: service.properties.display_name,
            url: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.SharedServices}/${service.id}`,
            key: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.SharedServices}/${service.id}`
          });
      });

      const serviceNavLinks: INavLinkGroup[] = [
        {
          links: [
            {
              name: 'Overview',
              key: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}`,
              url: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}`,
              isExpanded: true
            },
            {
              name: 'Services',
              key: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.WorkspaceServices}`,
              url: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.WorkspaceServices}`,
              isExpanded: true,
              links: serviceLinkArray
            },
            {
              name: 'Shared Services',
              key: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.SharedServices}`,
              url: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.SharedServices}`,
              isExpanded: false,
              links: sharedServiceLinkArray
            },
            {
              name: 'Users',
              key: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/users`,
              url: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/users`,
              isExpanded: false
            }
          ]
        }
      ];

      // Only show airlock link if enabled for workspace
      if (workspaceCtx.workspace.properties !== undefined && workspaceCtx.workspace.properties.enable_airlock) {
        serviceNavLinks[0].links.push({
          name: 'Airlock',
          key: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.AirlockRequests}`,
          url: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.AirlockRequests}`,
        });
      }

      setServiceLinks(serviceNavLinks);
    };
    getWorkspaceServices();
  }, [props.workspaceServices, props.sharedServices, workspaceCtx.workspace.id, workspaceCtx.workspace.properties]);

  return (
    <>
      <Nav
        onLinkClick={(e, item) => {
          e?.preventDefault();
          if (!item || !item.url) return;
          let selectedService = props.workspaceServices.find((w) => item.key?.indexOf(w.id.toString()) !== -1);
          if (selectedService) {
            props.setWorkspaceService(selectedService);
          }
          navigate(item.url)
        }}
        ariaLabel="TRE Workspace Left Navigation"
        groups={serviceLinks}
        styles={navStyles}
      />
    </>
  );
};

const navStyles: Partial<INavStyles> = {
  root: {
    boxSizing: 'border-box',
    border: '1px solid #eee',
    paddingBottom: 40
  },
  // these link styles override the default truncation behavior
  link: {
    whiteSpace: 'normal',
    lineHeight: 'inherit',
  },
};

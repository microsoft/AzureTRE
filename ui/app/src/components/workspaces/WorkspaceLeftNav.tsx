import React, { useContext, useEffect, useState } from 'react';
import { Nav, INavLinkGroup, INavStyles } from '@fluentui/react/lib/Nav';
import { useNavigate } from 'react-router-dom';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { WorkspaceService } from '../../models/workspaceService';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';

// TODO:
// - active item is sometimes lost

interface WorkspaceLeftNavProps {
  workspaceServices: Array<WorkspaceService>,
  setWorkspaceService: (workspaceService: WorkspaceService) => void,
  addWorkspaceService: (w: WorkspaceService) => void
}

export const WorkspaceLeftNav: React.FunctionComponent<WorkspaceLeftNavProps> = (props:WorkspaceLeftNavProps) => {
  const navigate = useNavigate();
  const emptyLinks: INavLinkGroup[] = [{links:[]}];
  const [serviceLinks, setServiceLinks] = useState(emptyLinks);
  const workspaceCtx = useContext(WorkspaceContext);

  useEffect(() => {
    const getWorkspaceServices = async () => {
      // get the workspace services

      let serviceLinkArray: Array<any> = [];
      props.workspaceServices.forEach((service: WorkspaceService) => {
        serviceLinkArray.push(
          {
            name: service.properties.display_name,
            url: `${ApiEndpoint.WorkspaceServices}/${service.id}`,
            key: service.id
          });
      });

      const seviceNavLinks: INavLinkGroup[] = [
        {
          links: [
            {
              name: 'Overview',
              key: 'overview',
              url: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}`,
              isExpanded: true
            },
            {
              name: 'Services',
              key: 'services',
              url: ApiEndpoint.WorkspaceServices,
              isExpanded: true,
              links: serviceLinkArray
            }
          ]
        }
      ];

      setServiceLinks(seviceNavLinks);
    };
    getWorkspaceServices();
  }, [props.workspaceServices, workspaceCtx.workspace]);

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
          navigate(item.url)}}
        ariaLabel="TRE Workspace Left Navigation"
        groups={serviceLinks}
        styles={navStyles}
      />
    </>
  );
};

const navStyles: Partial<INavStyles> = {
  root: {
    width: 208,
    height: 350,
    boxSizing: 'border-box',
    border: '1px solid #eee',
    overflowY: 'auto',
  },
  // these link styles override the default truncation behavior
  link: {
    whiteSpace: 'normal',
    lineHeight: 'inherit',
  },
};

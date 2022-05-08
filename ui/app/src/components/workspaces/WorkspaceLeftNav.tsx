import React, { useEffect, useState } from 'react';
import { Nav, INavLinkGroup } from '@fluentui/react/lib/Nav';
import { useNavigate } from 'react-router-dom';
import { Workspace } from '../../models/workspace';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { HttpMethod, useAuthApiCall } from '../../useAuthApiCall';
import { WorkspaceService } from '../../models/workspaceService';

// TODO:
// - we lose the selected styling when navigating into a user resource. This may not matter as the user resource page might die away.
// - loading placeholders / error content(?)

interface WorkspaceLeftNavProps {
  workspace: Workspace,
  setWorkspaceService: (workspaceService: WorkspaceService) => void
}

export const WorkspaceLeftNav: React.FunctionComponent<WorkspaceLeftNavProps> = (props:WorkspaceLeftNavProps) => {
  const navigate = useNavigate();
  const apiCall = useAuthApiCall();
  const emptyLinks: INavLinkGroup[] = [{links:[]}];
  const [serviceLinks, setServiceLinks] = useState(emptyLinks);
  const [workspaceServices, setWorkspaceServices] = useState([{} as WorkspaceService]);

  useEffect(() => {
    const getWorkspaceServices = async () => {
      // get the workspace services
      const ws = await apiCall(`${ApiEndpoint.Workspaces}/${props.workspace.id}/${ApiEndpoint.WorkspaceServices}`, HttpMethod.Get, props.workspace.properties.app_id);
      setWorkspaceServices(ws.workspaceServices);
      let serviceLinkArray: Array<any> = [];
      ws.workspaceServices.forEach((service: WorkspaceService) => {
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
              name: 'Services',
              key: 'services',
              url: '',
              isExpanded: true,
              links: serviceLinkArray
            }
          ]
        }
      ];
      
      setServiceLinks(seviceNavLinks);
    };
    getWorkspaceServices();
  }, [apiCall, props.workspace.id, props.workspace.properties.app_id]);

  return (
    <Nav
      onLinkClick={(e, item) => { 
        e?.preventDefault(); 
        if (!item || !item.url) return;
        let selectedService = workspaceServices.find((w) => w.id === item.key);
        if(selectedService) {
          console.log("You hit", selectedService);
          props.setWorkspaceService(selectedService);
        }
        navigate(item.url)}}
      ariaLabel="TRE Workspace Left Navigation"
      groups={serviceLinks}
    />
  );
};


import React, { useEffect, useState } from 'react';
import { Nav, INavLinkGroup } from '@fluentui/react/lib/Nav';
import { useNavigate } from 'react-router-dom';
import { Workspace } from '../../models/workspace';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { WorkspaceService } from '../../models/workspaceService';
import { CreateUpdateResource } from '../shared/CreateUpdateResource/CreateUpdateResource';
import { ResourceType } from '../../models/resourceType';
import { useBoolean } from '@fluentui/react-hooks';

// TODO:
// - we lose the selected styling when navigating into a user resource. This may not matter as the user resource page might die away.
// - loading placeholders / error content(?)

interface WorkspaceLeftNavProps {
  workspace: Workspace,
  workspaceServices: Array<WorkspaceService>,
  setWorkspaceService: (workspaceService: WorkspaceService) => void
}

export const WorkspaceLeftNav: React.FunctionComponent<WorkspaceLeftNavProps> = (props:WorkspaceLeftNavProps) => {
  const navigate = useNavigate();
  const emptyLinks: INavLinkGroup[] = [{links:[]}];
  const [serviceLinks, setServiceLinks] = useState(emptyLinks);
  const [createPanelOpen, { setTrue: createNew, setFalse: closeCreatePanel }] = useBoolean(false);
 
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

      // Add Create New link at the bottom of services links
      serviceLinkArray.push({
        name: "Create new",
        icon: "Add",
        key: "create"
      });

      const seviceNavLinks: INavLinkGroup[] = [
        {
          links: [
            {
              name: 'Overview',
              key: 'overview',
              url: `/${ApiEndpoint.Workspaces}/${props.workspace.id}`,
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
  }, [props.workspace.id, props.workspace.properties.app_id, props.workspaceServices]);

  return (
    <>
      <Nav
        onLinkClick={(e, item) => {
          e?.preventDefault();
          if (item?.key === "create") createNew();
          if (!item || !item.url) return;
          let selectedService = props.workspaceServices.find((w) => item.key?.indexOf(w.id.toString()) !== -1);
          if (selectedService) {
            props.setWorkspaceService(selectedService);
          }
          navigate(item.url)}}
        ariaLabel="TRE Workspace Left Navigation"
        groups={serviceLinks}
      />
      <CreateUpdateResource
        isOpen={createPanelOpen}
        onClose={closeCreatePanel}
        resourceType={ResourceType.WorkspaceService}
        parentResource={props.workspace}
      />
    </>
  );
};

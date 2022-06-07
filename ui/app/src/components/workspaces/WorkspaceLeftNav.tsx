import React, { useContext, useEffect, useState } from 'react';
import { Nav, INavLinkGroup, INavStyles } from '@fluentui/react/lib/Nav';
import { useNavigate } from 'react-router-dom';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { WorkspaceService } from '../../models/workspaceService';
import { ResourceType } from '../../models/resourceType';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import { Resource } from '../../models/resource';
import { CreateUpdateResourceContext } from '../../contexts/CreateUpdateResourceContext';
import { successStates } from '../../models/operation';

// TODO:
// - we lose the selected styling when navigating into a user resource. This may not matter as the user resource page might die away.
// - loading placeholders / error content(?)

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
  const createFormCtx = useContext(CreateUpdateResourceContext);

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
        key: "create",
        disabled: successStates.indexOf(workspaceCtx.workspace.deploymentStatus) === -1 || !workspaceCtx.workspace.isEnabled
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
          if (item?.key === "create") {
            createFormCtx.openCreateForm({
              resourceType: ResourceType.WorkspaceService,
              resourceParent: workspaceCtx.workspace,
              onAdd: (r: Resource) => props.addWorkspaceService(r as WorkspaceService),
              workspaceClientId: workspaceCtx.workspaceClientId
            })
          };
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

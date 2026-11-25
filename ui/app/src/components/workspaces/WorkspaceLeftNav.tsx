import React, { useContext, useEffect, useState } from "react";
import { Nav, INavLinkGroup, INavStyles } from "@fluentui/react/lib/Nav";
import { useNavigate } from "react-router-dom";
import { ApiEndpoint } from "../../models/apiEndpoints";
import { WorkspaceService } from "../../models/workspaceService";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { SharedService } from "../../models/sharedService";
import { successStates } from "../../models/operation";
import { RoleName, WorkspaceRoleName } from "../../models/roleNames";
import { AppRolesContext } from "../../contexts/AppRolesContext";

// TODO:
// - active item is sometimes lost

interface WorkspaceLeftNavProps {
  workspaceServices: Array<WorkspaceService>;
  sharedServices: Array<SharedService>;
  setWorkspaceService: (workspaceService: WorkspaceService) => void;
  addWorkspaceService: (w: WorkspaceService) => void;
  isTREAdminUser: boolean;
}

export const WorkspaceLeftNav: React.FunctionComponent<WorkspaceLeftNavProps> = (props: WorkspaceLeftNavProps) => {
  const navigate = useNavigate();
  const emptyLinks: INavLinkGroup[] = [{ links: [] }];
  const [serviceLinks, setServiceLinks] = useState(emptyLinks);
  const workspaceCtx = useContext(WorkspaceContext);
  const appRolesCtx = useContext(AppRolesContext);
  // TRE Admins keep owner-level navigation even when they also hold a non-owner workspace role.
  const canManageWorkspace =
    workspaceCtx.roles.includes(WorkspaceRoleName.WorkspaceOwner) || appRolesCtx.roles.includes(RoleName.TREAdmin);

  useEffect(() => {
    const getWorkspaceServices = async () => {
      // get the workspace services
      if (!workspaceCtx.workspace.id) return;
      let serviceLinkArray: Array<any> = [];
      let navLinks: INavLinkGroup[] = [{ links: [] }];

      if (!props.isTREAdminUser) {
        props.workspaceServices.forEach((service: WorkspaceService) => {
          serviceLinkArray.push({
            name: service.properties.display_name,
            url: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.WorkspaceServices}/${service.id}`,
            key: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.WorkspaceServices}/${service.id}`,
          });
        });

        let sharedServiceLinkArray: Array<any> = [];
        props.sharedServices.forEach((service: SharedService) => {
          sharedServiceLinkArray.push({
            name: service.properties.display_name,
            url: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.SharedServices}/${service.id}`,
            key: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.SharedServices}/${service.id}`,
          });
        });

        navLinks[0].links.push(
          {
            name: "Overview",
            key: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}`,
            url: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}`,
            isExpanded: true,
          },
          {
            name: "Services",
            key: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.WorkspaceServices}`,
            url: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.WorkspaceServices}`,
            isExpanded: true,
            links: serviceLinkArray,
          },
          ...(canManageWorkspace
            ? [
                {
                  name: "Shared Services",
                  key: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.SharedServices}`,
                  url: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.SharedServices}`,
                  isExpanded: false,
                  links: sharedServiceLinkArray,
                },
              ]
            : []),
        );

        // Only show airlock link if enabled for workspace
        if (workspaceCtx.workspace.properties !== undefined && workspaceCtx.workspace.properties.enable_airlock) {
          navLinks[0].links.push({
            name: "Airlock",
            key: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.AirlockRequests}`,
            url: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.AirlockRequests}`,
          });
        }
      }

      // Only add Users link if workspace is fully deployed; every workspace role and TRE Admins can list users.
      if (successStates.includes(workspaceCtx.workspace.deploymentStatus)) {
        navLinks[0].links.push({
          name: "Users",
          key: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.Users}`,
          url: `/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.Users}`,
          isExpanded: false,
        });
      }

      setServiceLinks(navLinks);
    };
    getWorkspaceServices();
  }, [
    props.workspaceServices,
    props.sharedServices,
    workspaceCtx.workspace.id,
    workspaceCtx.workspace.properties,
    workspaceCtx.workspace.deploymentStatus,
    canManageWorkspace,
  ]);

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
          navigate(item.url);
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
    boxSizing: "border-box",
    border: "1px solid #eee",
    paddingBottom: 40,
  },
  // these link styles override the default truncation behavior
  link: {
    whiteSpace: "normal",
    lineHeight: "inherit",
  },
};

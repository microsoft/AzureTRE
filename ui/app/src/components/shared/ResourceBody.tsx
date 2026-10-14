import React, { useContext } from "react";
import { ResourceDebug } from "../shared/ResourceDebug";
import { Pivot, PivotItem } from "@fluentui/react";
import { ResourcePropertyPanel } from "../shared/ResourcePropertyPanel";
import { Resource } from "../../models/resource";
import { ResourceHistoryList } from "../shared/ResourceHistoryList";
import { ResourceOperationsList } from "../shared/ResourceOperationsList";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { RoleName, WorkspaceRoleName } from "../../models/roleNames";
import { ResourceType } from "../../models/resourceType";
import { SecuredByRole } from "./SecuredByRole";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { AppRolesContext } from "../../contexts/AppRolesContext";

interface ResourceBodyProps {
  resource: Resource;
  readonly?: boolean;
}

// Module-level so the role arrays keep a stable identity across renders (they are effect dependencies downstream).
// Researchers get a simplified view: details of their own user resources, but not of workspaces or workspace services.
const detailsRolesByResourceType = {
  [ResourceType.Workspace]: [RoleName.TREAdmin, WorkspaceRoleName.WorkspaceOwner, WorkspaceRoleName.AirlockManager],
  [ResourceType.SharedService]: [RoleName.TREAdmin, WorkspaceRoleName.WorkspaceOwner],
  [ResourceType.WorkspaceService]: [
    RoleName.TREAdmin,
    WorkspaceRoleName.WorkspaceOwner,
    WorkspaceRoleName.AirlockManager,
  ],
  [ResourceType.UserResource]: [
    WorkspaceRoleName.WorkspaceOwner,
    WorkspaceRoleName.WorkspaceResearcher,
    WorkspaceRoleName.AirlockManager,
  ],
};

const operationsRolesByResourceType = {
  [ResourceType.Workspace]: [RoleName.TREAdmin, WorkspaceRoleName.WorkspaceOwner],
  [ResourceType.SharedService]: [RoleName.TREAdmin],
  [ResourceType.WorkspaceService]: [WorkspaceRoleName.WorkspaceOwner, WorkspaceRoleName.AirlockManager],
  [ResourceType.UserResource]: [
    WorkspaceRoleName.WorkspaceOwner,
    WorkspaceRoleName.WorkspaceResearcher,
    WorkspaceRoleName.AirlockManager,
  ],
};

const historyRolesByResourceType = {
  [ResourceType.Workspace]: [RoleName.TREAdmin, WorkspaceRoleName.WorkspaceOwner],
  [ResourceType.SharedService]: [RoleName.TREAdmin],
  [ResourceType.WorkspaceService]: [WorkspaceRoleName.WorkspaceOwner, WorkspaceRoleName.AirlockManager],
  [ResourceType.UserResource]: [
    WorkspaceRoleName.WorkspaceOwner,
    WorkspaceRoleName.WorkspaceResearcher,
    WorkspaceRoleName.AirlockManager,
  ],
};

export const ResourceBody: React.FunctionComponent<ResourceBodyProps> = (props: ResourceBodyProps) => {
  const workspaceCtx = useContext(WorkspaceContext);
  const appRolesCtx = useContext(AppRolesContext);
  const userRoles = [...appRolesCtx.roles, ...workspaceCtx.roles];
  const hasAnyRole = (roles?: Array<string>) => !!roles && roles.some((r) => userRoles.includes(r));

  const detailsRoles = detailsRolesByResourceType[props.resource.resourceType];
  const operationsRoles = operationsRolesByResourceType[props.resource.resourceType];
  const historyRoles = historyRolesByResourceType[props.resource.resourceType];
  const workspaceId = workspaceCtx.workspace?.id || "";

  return (
    <Pivot aria-label="Resource Menu" className="tre-resource-panel">
      <PivotItem
        headerText="Overview"
        headerButtonProps={{
          "data-order": 1,
          "data-title": "Overview",
        }}
      >
        <div style={{ padding: 5 }}>
          {props.readonly}
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {props.resource.properties?.overview || props.resource.properties?.description}
          </ReactMarkdown>
        </div>
      </PivotItem>
      {!props.readonly && hasAnyRole(detailsRoles) && (
        <PivotItem headerText="Details">
          <ResourcePropertyPanel resource={props.resource} />
          <ResourceDebug resource={props.resource} />
        </PivotItem>
      )}
      {!props.readonly && hasAnyRole(historyRoles) && (
        <PivotItem headerText="History">
          <SecuredByRole
            allowedAppRoles={historyRoles}
            allowedWorkspaceRoles={historyRoles}
            workspaceId={workspaceId}
            errorString={`Must have ${historyRoles.join(" or ")} role`}
            element={<ResourceHistoryList resource={props.resource} allowedRoles={historyRoles} />}
          />
        </PivotItem>
      )}
      {!props.readonly && hasAnyRole(operationsRoles) && (
        <PivotItem headerText="Operations">
          <SecuredByRole
            allowedAppRoles={operationsRoles}
            allowedWorkspaceRoles={operationsRoles}
            workspaceId={workspaceId}
            errorString={`Must have ${operationsRoles.join(" or ")} role`}
            element={<ResourceOperationsList resource={props.resource} allowedRoles={operationsRoles} />}
          />
        </PivotItem>
      )}
    </Pivot>
  );
};

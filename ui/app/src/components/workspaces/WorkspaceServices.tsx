import React, { useContext } from "react";
import { Resource } from "../../models/resource";
import { WorkspaceService } from "../../models/workspaceService";
import { ResourceCardList } from "../shared/ResourceCardList";
import { PrimaryButton, Stack } from "@fluentui/react";
import { ResourceType } from "../../models/resourceType";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { CreateUpdateResourceContext } from "../../contexts/CreateUpdateResourceContext";
import { successStates } from "../../models/operation";
import { WorkspaceRoleName } from "../../models/roleNames";
import { SecuredByRole } from "../shared/SecuredByRole";
import { RefreshButton } from "../shared/RefreshButton";
import { defaultSortOptions, ResourceListControls, useResourceListFilter } from "../shared/ResourceListControls";

const sortOptions = defaultSortOptions<WorkspaceService>();

interface WorkspaceServicesProps {
  workspaceServices: Array<WorkspaceService>;
  setWorkspaceService: (workspaceService: WorkspaceService) => void;
  addWorkspaceService: (workspaceService: WorkspaceService) => void;
  updateWorkspaceService: (workspaceService: WorkspaceService) => void;
  removeWorkspaceService: (workspaceService: WorkspaceService) => void;
  onRefresh?: () => void;
}

export const WorkspaceServices: React.FunctionComponent<WorkspaceServicesProps> = (props: WorkspaceServicesProps) => {
  const workspaceCtx = useContext(WorkspaceContext);
  const createFormCtx = useContext(CreateUpdateResourceContext);
  const { visibleResources, controlsProps } = useResourceListFilter(props.workspaceServices, {
    storageKey: "workspace-service",
    sortOptions,
  });

  return (
    <>
      <Stack className="tre-panel">
        <Stack.Item>
          <Stack horizontal horizontalAlign="space-between" verticalAlign="center">
            <h1>Workspace Services</h1>
            <Stack horizontal verticalAlign="center" tokens={{ childrenGap: 8 }}>
              <SecuredByRole
                allowedWorkspaceRoles={[WorkspaceRoleName.WorkspaceOwner]}
                element={
                  <PrimaryButton
                    iconProps={{ iconName: "Add" }}
                    text="Create new"
                    disabled={
                      successStates.indexOf(workspaceCtx.workspace.deploymentStatus) === -1 ||
                      !workspaceCtx.workspace.isEnabled
                    }
                    onClick={() => {
                      createFormCtx.openCreateForm({
                        resourceType: ResourceType.WorkspaceService,
                        resourceParent: workspaceCtx.workspace,
                        onAdd: (r: Resource) => props.addWorkspaceService(r as WorkspaceService),
                        workspaceApplicationIdURI: workspaceCtx.workspaceApplicationIdURI,
                      });
                    }}
                  />
                }
              />
              {props.onRefresh && <RefreshButton onClick={props.onRefresh} />}
            </Stack>
          </Stack>
        </Stack.Item>
        <Stack.Item>
          <ResourceListControls
            {...controlsProps}
            searchPlaceholder="Search services by name, ID or status..."
            ariaLabel="Workspace service list controls"
          />
        </Stack.Item>
        <Stack.Item>
          <ResourceCardList
            resources={visibleResources}
            selectResource={(r: Resource) => props.setWorkspaceService(r as WorkspaceService)}
            updateResource={(r: Resource) => props.updateWorkspaceService(r as WorkspaceService)}
            removeResource={(r: Resource) => props.removeWorkspaceService(r as WorkspaceService)}
            emptyText={
              controlsProps.search
                ? `No workspace services found matching "${controlsProps.search}".`
                : "This workspace has no workspace services."
            }
          />
        </Stack.Item>
      </Stack>
    </>
  );
};

import React, { useContext } from "react";
import { Workspace } from "../../models/workspace";

import { WorkspaceList } from "../workspaces/WorkspaceList";
import { Resource } from "../../models/resource";
import { PrimaryButton, Stack } from "@fluentui/react";
import { ResourceType } from "../../models/resourceType";
import { CreateUpdateResourceContext } from "../../contexts/CreateUpdateResourceContext";
import { RoleName } from "../../models/roleNames";
import { SecuredByRole } from "../shared/SecuredByRole";

interface RootDashboardProps {
  selectWorkspace?: (workspace: Workspace) => void;
  workspaces: Array<Workspace>;
  updateWorkspace: (w: Workspace) => void;
  removeWorkspace: (w: Workspace) => void;
  addWorkspace: (w: Workspace) => void;
}

export const RootDashboard: React.FunctionComponent<RootDashboardProps> = (
  props: RootDashboardProps,
) => {
  const createFormCtx = useContext(CreateUpdateResourceContext);

  return (
    <>
      <Stack className="tre-panel">
        <Stack.Item>
          <Stack horizontal horizontalAlign="space-between">
            <Stack.Item>
              <h1>Workspaces</h1>
            </Stack.Item>
            <Stack.Item style={{ width: 200, textAlign: "right" }}>
              <SecuredByRole
                allowedAppRoles={[RoleName.TREAdmin]}
                element={
                  <PrimaryButton
                    iconProps={{ iconName: "Add" }}
                    text="Create new"
                    onClick={() => {
                      createFormCtx.openCreateForm({
                        resourceType: ResourceType.Workspace,
                        onAdd: (r: Resource) =>
                          props.addWorkspace(r as Workspace),
                      });
                    }}
                  />
                }
              />
            </Stack.Item>
          </Stack>
        </Stack.Item>
        <Stack.Item>
          <WorkspaceList
            workspaces={props.workspaces}
            updateWorkspace={props.updateWorkspace}
            removeWorkspace={props.removeWorkspace}
            addWorkspace={props.addWorkspace}
          />
        </Stack.Item>
      </Stack>
    </>
  );
};

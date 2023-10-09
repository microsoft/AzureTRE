import React from "react";
import { Workspace } from "../models/workspace";
import { CostResource } from "../models/costs";

export const WorkspaceContext = React.createContext({
  roles: [] as Array<string>,
  costs: [] as Array<CostResource>,
  setCosts: (costs: Array<CostResource>) => { },
  setRoles: (roles: Array<string>) => { },
  setWorkspace: (w: Workspace) => { },
  workspace: {} as Workspace,
  workspaceApplicationIdURI: "" as string
});

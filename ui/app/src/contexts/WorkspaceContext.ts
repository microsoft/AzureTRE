import React from "react";
import { Workspace } from "../models/workspace";

export const WorkspaceContext = React.createContext({
  roles: [] as Array<string>,
  setRoles: (roles: Array<string>) => { },
  setWorkspace: (w: Workspace) => { },
  workspace: {} as Workspace,
  workspaceApplicationIdURI: "" as string
});

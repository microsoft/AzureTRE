import React from "react";
import { Workspace } from "../models/workspace";

export const WorkspaceContext = React.createContext({
  roles: [] as Array<string>,
  setRoles: (roles: Array<string>) => { },
  workspace: {} as Workspace,
  workspaceClientId: "" as string
});

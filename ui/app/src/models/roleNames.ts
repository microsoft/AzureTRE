export enum RoleName {
  TREAdmin = "TREAdmin",
  TREUser = "TREUser",
}

export enum WorkspaceRoleName {
  WorkspaceOwner = "WorkspaceOwner",
  WorkspaceResearcher = "WorkspaceResearcher",
  AirlockManager = "AirlockManager",
}

const friendlyRoleNames: Record<string, string> = {
  [RoleName.TREAdmin]: "TRE Administrator",
  [RoleName.TREUser]: "TRE User",
  [WorkspaceRoleName.WorkspaceOwner]: "Workspace Owner",
  [WorkspaceRoleName.WorkspaceResearcher]: "Workspace Researcher",
  [WorkspaceRoleName.AirlockManager]: "Airlock Manager",
};

export const getFriendlyRoleName = (role: string): string => friendlyRoleNames[role] || role;

export const coreRoleNames: Array<string> = [RoleName.TREAdmin, RoleName.TREUser];

export const workspaceRoleNames: Array<string> = [
  WorkspaceRoleName.WorkspaceOwner,
  WorkspaceRoleName.WorkspaceResearcher,
  WorkspaceRoleName.AirlockManager,
];

const roleDescriptions: Record<string, string> = {
  [RoleName.TREAdmin]: "Create and manage workspaces and shared services.",
  [RoleName.TREUser]: "Sign in to the TRE and open workspaces you belong to.",
  [WorkspaceRoleName.WorkspaceOwner]: "Manage the workspace, its services, users and user resources.",
  [WorkspaceRoleName.WorkspaceResearcher]: "Use workspace services and create your own user resources.",
  [WorkspaceRoleName.AirlockManager]: "Review and approve or reject airlock import and export requests.",
};

export const getRoleDescription = (role: string): string => roleDescriptions[role] || "";

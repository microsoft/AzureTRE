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

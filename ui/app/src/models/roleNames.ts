export enum RoleName {
  TREAdmin = "TREAdmin",
  TREUser = "TREUser",
}

export enum WorkspaceRoleName {
  WorkspaceOwner = "WorkspaceOwner",
  WorkspaceResearcher = "WorkspaceResearcher",
  AirlockManager = "AirlockManager",
}

// Display names for the app roles defined in the core and workspace app
// registrations. Tokens carry the raw role value, which is what the RBAC checks
// compare against, but it is not what we want to put in front of a user.
const roleDisplayNames: Record<string, string> = {
  [RoleName.TREAdmin]: "TRE Administrator",
  [RoleName.TREUser]: "TRE User",
  [WorkspaceRoleName.WorkspaceOwner]: "Workspace Owner",
  [WorkspaceRoleName.WorkspaceResearcher]: "Workspace Researcher",
  [WorkspaceRoleName.AirlockManager]: "Airlock Manager",
};

// Falls back to the raw value so that a role added to an app registration
// without a matching entry here is still shown rather than silently dropped.
export const getRoleDisplayName = (role: string): string => roleDisplayNames[role] ?? role;

// Most to least privileged, within each scope. A token lists roles in no
// guaranteed order, so anywhere only one role fits we want it to be the one
// that says the most about what the user can do. Unlisted roles sort last.
const rolePrecedence: Array<string> = [
  RoleName.TREAdmin,
  RoleName.TREUser,
  WorkspaceRoleName.WorkspaceOwner,
  WorkspaceRoleName.AirlockManager,
  WorkspaceRoleName.WorkspaceResearcher,
];

export const orderRoles = (roles: Array<string>): Array<string> =>
  [...roles].sort((a, b) => {
    const rank = (role: string) => {
      const i = rolePrecedence.indexOf(role);
      return i === -1 ? rolePrecedence.length : i;
    };
    return rank(a) - rank(b);
  });

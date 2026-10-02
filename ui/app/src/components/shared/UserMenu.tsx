import React, { useContext } from "react";
import { IContextualMenuProps, Persona, PersonaSize, PrimaryButton } from "@fluentui/react";
import { useAccount, useMsal } from "@azure/msal-react";
import { AppRolesContext } from "../../contexts/AppRolesContext";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { getFriendlyRoleName } from "../../models/roleNames";

export const UserMenu: React.FunctionComponent = () => {
  const { instance, accounts } = useMsal();
  const account = useAccount(accounts[0] || {});
  const appRoles = useContext(AppRolesContext);
  const workspace = useContext(WorkspaceContext);
  const coreRoles = appRoles.roles.map(getFriendlyRoleName);
  const workspaceRoles = workspace.roles.map(getFriendlyRoleName);
  const roleSummary = workspace.workspace.id
    ? workspaceRoles.length
      ? [...coreRoles, ...workspaceRoles].join(" · ")
      : coreRoles.length
        ? [...coreRoles, "No workspace roles assigned"].join(" · ")
        : "No roles assigned"
    : coreRoles.join(" · ") || "No roles assigned";

  const menuProps: IContextualMenuProps = {
    shouldFocusOnMount: true,
    directionalHint: 6, // bottom right edge
    items: [
      {
        key: "logout",
        text: "Logout",
        iconProps: { iconName: "SignOut" },
        onClick: () => {
          instance.logout(); // will use MSAL to logout and redirect to the /logout page
        },
      },
    ],
  };

  return (
    <div className="tre-user-menu">
      <PrimaryButton menuProps={menuProps} style={{ background: "none", border: "none" }}>
        <Persona text={account?.name} secondaryText={roleSummary} size={PersonaSize.size32} imageAlt={account?.name} />
      </PrimaryButton>
    </div>
  );
};

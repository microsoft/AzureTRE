import React, { useContext, useState } from "react";
import { ContextualMenuItemType, IContextualMenuProps, Persona, PersonaSize, PrimaryButton } from "@fluentui/react";
import { useAccount, useMsal } from "@azure/msal-react";
import { AppRolesContext } from "../../contexts/AppRolesContext";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { UserAccessPanel } from "./UserAccessPanel";

export const UserMenu: React.FunctionComponent = () => {
  const { instance, accounts } = useMsal();
  const account = useAccount(accounts[0] || {});
  const appRoles = useContext(AppRolesContext);
  const workspace = useContext(WorkspaceContext);
  const [showAccess, setShowAccess] = useState(false);

  const workspaceName = workspace.workspace?.id
    ? workspace.workspace.properties?.display_name || workspace.workspace.id
    : undefined;

  const logout = () => {
    instance.logout(); // will use MSAL to logout and redirect to the /logout page
  };

  const menuProps: IContextualMenuProps = {
    shouldFocusOnMount: true,
    directionalHint: 6, // bottom right edge
    items: [
      {
        key: "user",
        itemType: ContextualMenuItemType.Header,
        text:
          account?.name && account?.username
            ? `${account.name} (${account.username})`
            : account?.name || account?.username,
      },
      {
        key: "access",
        text: "Your access...",
        iconProps: { iconName: "Permissions" },
        onClick: () => setShowAccess(true),
      },
      {
        key: "logout",
        text: "Logout",
        iconProps: { iconName: "SignOut" },
        onClick: logout,
      },
    ],
  };

  return (
    <div className="tre-user-menu">
      <PrimaryButton menuProps={menuProps} style={{ background: "none", border: "none" }}>
        <Persona text={account?.name} size={PersonaSize.size32} imageAlt={account?.name} />
      </PrimaryButton>
      <UserAccessPanel
        isOpen={showAccess}
        onDismiss={() => setShowAccess(false)}
        onSignOut={logout}
        userName={account?.name}
        userEmail={account?.username}
        coreRoles={appRoles.roles || []}
        workspaceRoles={workspace.roles || []}
        workspaceName={workspaceName}
      />
    </div>
  );
};

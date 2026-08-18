import React, { useContext } from "react";
import {
  ContextualMenuItemType,
  getTheme,
  IContextualMenuItem,
  IContextualMenuProps,
  Persona,
  PersonaSize,
  PrimaryButton,
} from "@fluentui/react";
import { useAccount, useMsal } from "@azure/msal-react";
import { useLocation } from "react-router-dom";
import { AppRolesContext } from "../../contexts/AppRolesContext";
import { getRoleDisplayName, orderRoles } from "../../models/roleNames";

interface UserMenuProps {
  // Roles the user holds in the workspace they are currently viewing. Empty
  // outside a workspace: WorkspaceProvider clears them when it unmounts.
  workspaceRoles?: Array<string>;
}

// One menu section per role scope. An explicit "None assigned" entry keeps the
// section present when the user holds no role in that scope, which is the state
// that is otherwise indistinguishable from a role that has not taken effect yet.
const roleMenuSection = (key: string, title: string, roles: Array<string>): Array<IContextualMenuItem> => {
  const section: Array<IContextualMenuItem> = [
    { key: `${key}-divider`, itemType: ContextualMenuItemType.Divider },
    { key: `${key}-header`, itemType: ContextualMenuItemType.Header, text: title },
  ];

  if (roles.length === 0) {
    return [...section, { key: `${key}-none`, text: "None assigned" }];
  }

  return [
    ...section,
    ...orderRoles(roles).map((role) => ({
      key: `${key}-${role}`,
      text: getRoleDisplayName(role),
      iconProps: { iconName: "Contact" },
    })),
  ];
};

const theme = getTheme();

export const UserMenu: React.FunctionComponent<UserMenuProps> = (props: UserMenuProps) => {
  const { instance, accounts } = useMsal();
  const account = useAccount(accounts[0] || {});
  const appRoles = useContext(AppRolesContext);
  const location = useLocation();

  const workspaceRoles = props.workspaceRoles ?? [];
  // The workspace roles section is shown for any workspace route, including when
  // the user holds no role there. That is the TRE Admin case, and hiding the
  // section would make it look the same as not being in a workspace at all.
  const inWorkspace = location.pathname.startsWith("/workspaces/");

  // Both scopes are listed in the menu, but the button itself has room for one
  // line only, so it shows the roles for the scope the user is looking at. A TRE
  // Admin viewing a workspace holds no workspace role, and falls back to the
  // core roles rather than being told that no role is assigned.
  const summaryRoles = orderRoles(workspaceRoles.length > 0 ? workspaceRoles : appRoles.roles);

  // Listing every role here either overflows the bar or gets cut off mid word,
  // and a clipped list does not say how much it left out. Name the most
  // privileged role in full and count the rest; the menu has the full list.
  const roleSummary =
    summaryRoles.length === 0
      ? "No roles assigned"
      : summaryRoles.length === 1
        ? getRoleDisplayName(summaryRoles[0])
        : `${getRoleDisplayName(summaryRoles[0])} +${summaryRoles.length - 1} more`;

  const menuProps: IContextualMenuProps = {
    shouldFocusOnMount: true,
    directionalHint: 6, // bottom right edge
    items: [
      ...roleMenuSection("tre-roles", "TRE roles", appRoles.roles),
      ...(inWorkspace ? roleMenuSection("workspace-roles", "Workspace roles", workspaceRoles) : []),
      { key: "logout-divider", itemType: ContextualMenuItemType.Divider },
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
        <Persona
          text={account?.name}
          secondaryText={roleSummary}
          // size40 is the smallest size at which Fluent renders the secondary
          // text line, which is what carries the role summary.
          size={PersonaSize.size40}
          imageAlt={account?.name}
          // Bounded so that a user holding several roles cannot push the rest of
          // the top bar off screen. Fluent truncates what does not fit.
          styles={{ root: { maxWidth: 240 }, secondaryText: { color: theme.palette.white } }}
        />
      </PrimaryButton>
    </div>
  );
};

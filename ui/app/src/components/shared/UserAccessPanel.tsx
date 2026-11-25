import React from "react";
import {
  DefaultButton,
  FontWeights,
  Icon,
  MessageBar,
  MessageBarType,
  Panel,
  PanelType,
  Persona,
  PersonaSize,
  Stack,
  Text,
  getTheme,
  mergeStyles,
} from "@fluentui/react";
import {
  coreRoleNames,
  getFriendlyRoleName,
  getRoleDescription,
  RoleName,
  workspaceRoleNames,
} from "../../models/roleNames";

interface UserAccessPanelProps {
  isOpen: boolean;
  onDismiss: () => void;
  onSignOut: () => void;
  userName?: string;
  userEmail?: string;
  coreRoles: Array<string>;
  workspaceRoles: Array<string>;
  workspaceName?: string;
}

const theme = getTheme();

const sectionClass = mergeStyles({ marginTop: 24 });

const sectionHeaderClass = mergeStyles({
  fontWeight: FontWeights.semibold,
});

const mutedClass = mergeStyles({ color: theme.palette.neutralSecondary });

const notHeldClass = mergeStyles({ color: theme.palette.neutralTertiary });

const RoleList: React.FunctionComponent<{ allRoles: Array<string>; heldRoles: Array<string> }> = (props) => {
  // Include any held roles the UI does not know about, so the panel always matches the token.
  const roles = [...props.allRoles, ...props.heldRoles.filter((r) => !props.allRoles.includes(r))];
  const held = roles.filter((r) => props.heldRoles.includes(r));
  const notHeld = roles.filter((r) => !props.heldRoles.includes(r));
  return (
    <Stack tokens={{ childrenGap: 12 }} styles={{ root: { marginTop: 8 } }}>
      {held.map((role) => (
        <Stack key={role} horizontal tokens={{ childrenGap: 10 }} data-testid={`role-held-${role}`}>
          <Icon
            iconName="CompletedSolid"
            aria-hidden
            styles={{ root: { color: theme.palette.green, fontSize: 16, marginTop: 2 } }}
          />
          <Stack>
            <Text className={sectionHeaderClass}>{getFriendlyRoleName(role)}</Text>
            {getRoleDescription(role) && (
              <Text variant="small" className={mutedClass}>
                {getRoleDescription(role)}
              </Text>
            )}
          </Stack>
        </Stack>
      ))}
      {notHeld.map((role) => (
        <Stack
          key={role}
          horizontal
          verticalAlign="center"
          tokens={{ childrenGap: 10 }}
          className={notHeldClass}
          data-testid={`role-not-held-${role}`}
        >
          <Icon iconName="CircleRing" aria-hidden styles={{ root: { fontSize: 16 } }} />
          <Text className={notHeldClass}>
            {getFriendlyRoleName(role)}
            <Text variant="small" className={notHeldClass}>
              {" "}
              — not assigned
            </Text>
          </Text>
        </Stack>
      ))}
    </Stack>
  );
};

export const UserAccessPanel: React.FunctionComponent<UserAccessPanelProps> = (props) => {
  const footer = () => (
    <Stack tokens={{ childrenGap: 8 }}>
      <Text variant="small" className={mutedClass}>
        Roles come from your sign-in token. Role changes made after sign-in appear only after you sign in again.
      </Text>
      <Stack horizontal>
        <DefaultButton iconProps={{ iconName: "SignOut" }} text="Sign out and back in" onClick={props.onSignOut} />
      </Stack>
    </Stack>
  );

  return (
    <Panel
      isOpen={props.isOpen}
      onDismiss={props.onDismiss}
      headerText="Your access"
      type={PanelType.smallFixedFar}
      isLightDismiss
      closeButtonAriaLabel="Close"
      onRenderFooterContent={footer}
      isFooterAtBottom
    >
      <Persona
        text={props.userName}
        secondaryText={props.userEmail}
        size={PersonaSize.size40}
        styles={{ root: { marginTop: 8 } }}
      />

      <div className={sectionClass}>
        <Text block variant="mediumPlus" className={sectionHeaderClass}>
          TRE roles
        </Text>
        <RoleList allRoles={coreRoleNames} heldRoles={props.coreRoles} />
      </div>

      {props.workspaceName !== undefined && (
        <div className={sectionClass}>
          <Text block variant="mediumPlus" className={sectionHeaderClass}>
            Workspace roles
          </Text>
          <Text block variant="small" className={mutedClass}>
            {props.workspaceName}
          </Text>
          {props.workspaceRoles.length === 0 && (
            <MessageBar messageBarType={MessageBarType.warning} isMultiline styles={{ root: { marginTop: 8 } }}>
              {props.coreRoles.includes(RoleName.TREAdmin)
                ? "No workspace role. You are viewing this workspace as a TRE Administrator; some workspace actions require a workspace role."
                : "No workspace role assigned."}
            </MessageBar>
          )}
          <RoleList allRoles={workspaceRoleNames} heldRoles={props.workspaceRoles} />
        </div>
      )}
    </Panel>
  );
};

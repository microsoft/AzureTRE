import React from "react";
import {
  DefaultButton,
  MessageBar,
  MessageBarType,
  Panel,
  PanelType,
  Stack,
  Text,
  getTheme,
  mergeStyles,
} from "@fluentui/react";
import moment from "moment";
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
  tokenIssuedAt?: number;
  coreRoles: Array<string>;
  workspaceRoles: Array<string>;
  workspaceName?: string;
}

const theme = getTheme();

const heldRoleClass = mergeStyles({
  border: `1px solid ${theme.palette.neutralLight}`,
  borderLeft: `3px solid ${theme.palette.green}`,
  padding: "8px 12px",
});

const notHeldRoleClass = mergeStyles({
  border: `1px dashed ${theme.palette.neutralLight}`,
  padding: "6px 12px",
  color: theme.palette.neutralTertiary,
});

const sectionHeaderClass = mergeStyles({
  textTransform: "uppercase",
  letterSpacing: "1px",
  fontWeight: 600,
  marginTop: 20,
  marginBottom: 6,
});

const RoleList: React.FunctionComponent<{ allRoles: Array<string>; heldRoles: Array<string> }> = (props) => {
  // Include any held roles the UI does not know about, so the panel always matches the token.
  const roles = [...props.allRoles, ...props.heldRoles.filter((r) => !props.allRoles.includes(r))];
  return (
    <Stack tokens={{ childrenGap: 6 }}>
      {roles.map((role) =>
        props.heldRoles.includes(role) ? (
          <div key={role} className={heldRoleClass} data-testid={`role-held-${role}`}>
            <Text block variant="mediumPlus">
              {getFriendlyRoleName(role)}
            </Text>
            {getRoleDescription(role) && (
              <Text block variant="small">
                {getRoleDescription(role)}
              </Text>
            )}
          </div>
        ) : (
          <div key={role} className={notHeldRoleClass} data-testid={`role-not-held-${role}`}>
            <Text>{getFriendlyRoleName(role)} — not assigned</Text>
          </div>
        ),
      )}
    </Stack>
  );
};

export const UserAccessPanel: React.FunctionComponent<UserAccessPanelProps> = (props) => {
  const issuedAt = props.tokenIssuedAt ? moment.unix(props.tokenIssuedAt).format("HH:mm") : undefined;

  return (
    <Panel
      isOpen={props.isOpen}
      onDismiss={props.onDismiss}
      headerText="Your access"
      type={PanelType.smallFixedFar}
      isLightDismiss
      closeButtonAriaLabel="Close"
    >
      <Text block style={{ marginBottom: 12 }}>
        {[props.userName, props.userEmail].filter(Boolean).join(" · ")}
      </Text>

      <MessageBar messageBarType={MessageBarType.info} isMultiline>
        <Text block>
          Roles come from your sign-in token
          {issuedAt ? (
            <>
              , issued at <b>{issuedAt}</b>
            </>
          ) : null}
          . A role assigned after that time will not appear until you sign in again.
        </Text>
        <DefaultButton text="Sign out and back in" onClick={props.onSignOut} style={{ marginTop: 8 }} />
      </MessageBar>

      <Text block className={sectionHeaderClass}>
        TRE
      </Text>
      <RoleList allRoles={coreRoleNames} heldRoles={props.coreRoles} />

      {props.workspaceName !== undefined && (
        <>
          <Text block className={sectionHeaderClass}>
            Workspace · {props.workspaceName}
          </Text>
          {props.workspaceRoles.length === 0 && (
            <MessageBar messageBarType={MessageBarType.warning} isMultiline style={{ marginBottom: 6 }}>
              {props.coreRoles.includes(RoleName.TREAdmin)
                ? "No workspace role. You are viewing this workspace as a TRE Administrator; workspace-level actions require a workspace role."
                : "No workspace role assigned."}
            </MessageBar>
          )}
          <RoleList allRoles={workspaceRoleNames} heldRoles={props.workspaceRoles} />
        </>
      )}
    </Panel>
  );
};

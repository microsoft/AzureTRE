import React from "react";
import { FontIcon, getTheme, IconButton, mergeStyles, Text, TooltipHost } from "@fluentui/react";
import moment from "moment";
import { awaitingStates, failedStates, inProgressStates, successStates } from "../../models/operation";
import { User } from "../../models/user";

const theme = getTheme();

const gridClass = mergeStyles({
  display: "grid",
  gridTemplateColumns: "200px minmax(0, 1fr)",
  columnGap: "24px",
  rowGap: "8px",
  alignItems: "baseline",
});

const labelClass = mergeStyles({ color: theme.palette.neutralSecondary });

const valueClass = mergeStyles({ wordBreak: "break-word", minWidth: 0 });

export const sectionHeaderClass = mergeStyles({
  fontWeight: 600,
  margin: "16px 0 8px",
});

export interface PropertyGridItem {
  label: string;
  value: React.ReactNode;
  copyValue?: string;
}

// Two-column label/value layout used by the resource Details tab.
export const PropertyGrid: React.FunctionComponent<{ items: Array<PropertyGridItem> }> = ({ items }) => (
  <div className={gridClass}>
    {items.map((item) => (
      <React.Fragment key={item.label}>
        <Text className={labelClass}>{item.label}</Text>
        <div className={valueClass}>
          <Text>{item.value}</Text>
          {item.copyValue && (
            <IconButton
              iconProps={{ iconName: "Copy" }}
              title={`Copy ${item.label.toLowerCase()}`}
              ariaLabel={`Copy ${item.label.toLowerCase()}`}
              styles={{ root: { height: 20, width: 24, marginLeft: 4, verticalAlign: "middle" } }}
              onClick={() => navigator.clipboard?.writeText(item.copyValue as string)}
            />
          )}
        </div>
      </React.Fragment>
    ))}
  </div>
);

// Relative time ("2 hours ago") with the exact time on hover.
export const RelativeTime: React.FunctionComponent<{ unixTime: number }> = ({ unixTime }) => {
  const time = moment.unix(unixTime);
  return (
    <TooltipHost content={time.format("LLLL")}>
      <Text>{time.fromNow()}</Text>
    </TooltipHost>
  );
};

export const userDisplayName = (user?: Partial<User>) => user?.name || user?.email || user?.id || "—";

export const statusLabel = (status?: string) => (status ? status.replace(/_/g, " ") : "");

export const StatusIcon: React.FunctionComponent<{ status?: string }> = ({ status }) => {
  let iconName = "Info";
  let color = theme.palette.neutralSecondary;
  if (status && successStates.includes(status)) {
    iconName = "CompletedSolid";
    color = theme.palette.green;
  } else if (status && failedStates.includes(status)) {
    iconName = "StatusErrorFull";
    color = theme.palette.redDark;
  } else if (status && awaitingStates.includes(status)) {
    iconName = "Clock";
  } else if (status && inProgressStates.includes(status)) {
    iconName = "Sync";
    color = theme.palette.themePrimary;
  }
  return <FontIcon iconName={iconName} aria-hidden style={{ color, fontSize: 16 }} />;
};

// API scope for a role-restricted list: the workspace scope when a workspace role grants access, otherwise the
// core scope (""), which carries TRE-level roles such as TREAdmin.
export const getListApiScope = (
  workspaceRoles: Array<string> | undefined,
  workspaceScopeId: string | undefined,
  allowedRoles?: Array<string>,
) => {
  const roles = workspaceRoles || [];
  const grantedByWorkspace = allowedRoles ? roles.some((r) => allowedRoles.includes(r)) : roles.length > 0;
  return grantedByWorkspace ? workspaceScopeId || "" : "";
};

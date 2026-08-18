import React from "react";
import { getTheme, Icon, mergeStyles, Stack } from "@fluentui/react";
import { Link } from "react-router-dom";
import { UserMenu } from "./UserMenu";
import { NotificationPanel } from "./notifications/NotificationPanel";
import config from "../../config.json";

interface TopNavProps {
  // Passed through to the user menu, which sits outside the WorkspaceContext
  // provider and so cannot read the workspace roles itself.
  workspaceRoles?: Array<string>;
}

export const TopNav: React.FunctionComponent<TopNavProps> = (props: TopNavProps) => {
  return (
    <>
      <div className={contentClass}>
        <Stack horizontal>
          <Stack.Item grow={100}>
            <Link to="/" className="tre-home-link">
              <Icon
                iconName="TestBeakerSolid"
                style={{
                  marginLeft: "10px",
                  marginRight: "10px",
                  verticalAlign: "middle",
                }}
              />
              <h5 style={{ display: "inline" }}>
                {(config.uiSiteName ?? "") === "" ? "Azure TRE" : config.uiSiteName}
              </h5>
            </Link>
          </Stack.Item>
          <Stack.Item>
            <NotificationPanel />
          </Stack.Item>
          <Stack.Item grow>
            <UserMenu workspaceRoles={props.workspaceRoles} />
          </Stack.Item>
        </Stack>
      </div>
    </>
  );
};

const theme = getTheme();
const contentClass = mergeStyles([
  {
    backgroundColor: theme.palette.themeDark,
    color: theme.palette.white,
    lineHeight: "50px",
    padding: "0 10px 0 10px",
  },
]);

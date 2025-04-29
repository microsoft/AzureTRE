import React from "react";
import { getTheme, Icon, mergeStyles, Stack, Image, ImageFit } from "@fluentui/react";
import { Link } from "react-router-dom";
import { UserMenu } from "./UserMenu";
import { NotificationPanel } from "./notifications/NotificationPanel";

export const TopNav: React.FunctionComponent = () => {
  return (
    <>
      <div className={contentClass}>
        <Stack horizontal>
          <Stack.Item grow={100}>
            <Link to="/" className="tre-home-link">
              <Image
                src="/images/SPECTRE_HD_Logo.jpg"
                height={50}
                imageFit={ImageFit.contain}
                styles={{ root: { marginLeft: 10, marginRight: 10, verticalAlign: "middle" } }}
              />
            </Link>
          </Stack.Item>
          <Stack.Item>
            <NotificationPanel />
          </Stack.Item>
          <Stack.Item grow>
            <UserMenu />
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

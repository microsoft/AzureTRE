import React from "react";
import { getTheme, mergeStyles, Stack } from "@fluentui/react";
import { Link } from "react-router-dom";
import { UserMenu } from "./UserMenu";
import { NotificationPanel } from "./notifications/NotificationPanel";
import config from "../../config.json";

export const TopNav: React.FunctionComponent = () => {
  return (
    <>
      <div className={contentClass}>
        <Stack horizontal verticalAlign="center" styles={{ root: { width: "100%" } }}>
          <Stack.Item>
            <Link
              to="/"
              className="tre-home-link"
              style={{
                display: "inline-flex",
                alignItems: "center",
                textDecoration: "none",
              }}
            >
              <img
                src="/images/avatar.png"
                alt="Logo"
                width={50}
                height={50}
                style={{ marginRight: "12px" }}
              />
              <span className="service-name">
                <span className="service-name-line1">University of Oxford</span>
                <span className="service-name-line2">
                  Trusted Research Environment
                </span>
              </span>
            </Link>
          </Stack.Item>
          <Stack.Item style={{ marginLeft: "auto" }}>
            <Stack horizontal verticalAlign="center" tokens={{ childrenGap: 16 }}>
              <Stack.Item>
                <NotificationPanel />
              </Stack.Item>
              <Stack.Item>
                <UserMenu />
              </Stack.Item>
            </Stack>
          </Stack.Item>
        </Stack>
      </div>
    </>
  );
};

const theme = getTheme();
const contentClass = mergeStyles([
  {
    backgroundColor: "#002147",
    color: "#ffffff",
    padding: "0 32px",
    height: 70,
    display: "flex",
    alignItems: "center",
    boxShadow: "0 2px 4px rgba(0, 0, 0, 0.1)",
  },
]);

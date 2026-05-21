import { Link, MessageBar, MessageBarType } from "@fluentui/react";
import React from "react";
import { Link as RouterLink } from "react-router-dom";

export const NotFoundLayout: React.FunctionComponent = () => {
  return (
    <MessageBar messageBarType={MessageBarType.error} isMultiline={true}>
      <h2>404 - Page not found</h2>
      <p>The page you are looking for does not exist.</p>
      <Link as={RouterLink} to="/">
        Go to home page
      </Link>
    </MessageBar>
  );
};

import { CommandBarButton, getTheme } from "@fluentui/react";
import React from "react";

interface RefreshButtonProps {
  onClick: () => void;
}

const theme = getTheme();

// Borderless command-bar style so it matches the action bars it sits beside. Place it at the far right of a view.
export const RefreshButton: React.FunctionComponent<RefreshButtonProps> = ({ onClick }) => (
  <CommandBarButton
    iconProps={{ iconName: "Refresh" }}
    text="Refresh"
    ariaLabel="Refresh"
    styles={{ root: { background: "none", color: theme.palette.themePrimary, height: 40 } }}
    onClick={onClick}
  />
);

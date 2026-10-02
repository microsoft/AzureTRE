import { DefaultButton } from "@fluentui/react";
import React from "react";

interface RefreshButtonProps {
  onClick: () => void;
}

export const RefreshButton: React.FunctionComponent<RefreshButtonProps> = ({ onClick }) => (
  <DefaultButton iconProps={{ iconName: "Refresh" }} text="Refresh" onClick={onClick} />
);

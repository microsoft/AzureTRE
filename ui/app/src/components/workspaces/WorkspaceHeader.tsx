import { getTheme, Icon, mergeStyles, Stack } from "@fluentui/react";
import React, { useContext } from "react";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { RefreshButton } from "../shared/RefreshButton";

interface WorkspaceHeaderProps {
  onRefresh: () => void;
}

export const WorkspaceHeader: React.FunctionComponent<WorkspaceHeaderProps> = ({ onRefresh }) => {
  const workspaceCtx = useContext(WorkspaceContext);

  return (
    <>
      <Stack className={contentClass}>
        <Stack.Item className="tre-workspace-header">
          <Stack horizontal horizontalAlign="space-between" verticalAlign="center">
          <h4 style={{ fontWeight: "400" }}>
            <Icon
              iconName="CubeShape"
              style={{
                marginRight: "8px",
                fontSize: "22px",
                verticalAlign: "bottom",
              }}
            />
            {workspaceCtx.workspace?.properties?.display_name}
          </h4>
            <RefreshButton onClick={onRefresh} />
          </Stack>
        </Stack.Item>
      </Stack>
    </>
  );
};

const theme = getTheme();
const contentClass = mergeStyles([
  {
    backgroundColor: theme.palette.themeDarker,
    color: theme.palette.white,
    lineHeight: "15px",
    padding: "0 20px",
    boxShadow: "0 1px 8px 0px #ccc",
  },
]);

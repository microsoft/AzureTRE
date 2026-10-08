import React, { useCallback, useContext, useMemo } from "react";
import { ICommandBarItemProps, Stack } from "@fluentui/react";
import { Workspace } from "../../models/workspace";
import { ResourceCardList } from "../shared/ResourceCardList";
import { Resource } from "../../models/resource";
import { CostsContext } from "../../contexts/CostsContext";
import {
  ResourceListControls,
  ResourceSortOption,
  nameSortOption,
  statusSortOption,
  updatedSortOption,
  useResourceListFilter,
} from "../shared/ResourceListControls";

interface WorkspaceListProps {
  workspaces: Array<Workspace>;
  updateWorkspace: (w: Workspace) => void;
  removeWorkspace: (w: Workspace) => void;
  addWorkspace: (w: Workspace) => void;
  onRefresh?: () => void;
}

export const WorkspaceList: React.FunctionComponent<WorkspaceListProps> = ({
  workspaces,
  updateWorkspace,
  removeWorkspace,
  onRefresh,
}) => {
  const costsCtx = useContext(CostsContext);

  // Latest cost for a workspace (costs are assumed to be sorted by date)
  const getWorkspaceCost = useCallback(
    (workspaceId: string): number => {
      const workspaceCost = costsCtx.costs.find((cost) => cost.id === workspaceId);
      return workspaceCost && workspaceCost.costs.length > 0
        ? workspaceCost.costs[workspaceCost.costs.length - 1].cost
        : 0;
    },
    [costsCtx.costs],
  );

  const sortOptions = useMemo<Array<ResourceSortOption<Workspace>>>(
    () => [
      nameSortOption<Workspace>(),
      { key: "id", text: "ID", compare: (a, b) => a.id.localeCompare(b.id) },
      statusSortOption<Workspace>(),
      updatedSortOption<Workspace>(),
      { key: "cost", text: "Cost", compare: (a, b) => getWorkspaceCost(a.id) - getWorkspaceCost(b.id) },
    ],
    [getWorkspaceCost],
  );

  const { visibleResources, controlsProps } = useResourceListFilter(workspaces, {
    storageKey: "workspace",
    sortOptions,
  });

  const refreshItems: Array<ICommandBarItemProps> = onRefresh
    ? [
        {
          key: "refresh",
          text: "Refresh",
          ariaLabel: "Refresh",
          iconProps: { iconName: "Refresh" },
          onClick: onRefresh,
        },
      ]
    : [];

  return (
    <Stack>
      <Stack.Item>
        <ResourceListControls
          {...controlsProps}
          searchPlaceholder="Search workspaces by name or ID..."
          ariaLabel="Workspace list controls"
          farItems={refreshItems}
        />
      </Stack.Item>
      <Stack.Item>
        <ResourceCardList
          resources={visibleResources}
          updateResource={(r: Resource) => updateWorkspace(r as Workspace)}
          removeResource={(r: Resource) => removeWorkspace(r as Workspace)}
          emptyText={
            controlsProps.search
              ? `No workspaces found matching "${controlsProps.search}". Try a different search term.`
              : "No workspaces to display. Create one to get started."
          }
        />
      </Stack.Item>
    </Stack>
  );
};

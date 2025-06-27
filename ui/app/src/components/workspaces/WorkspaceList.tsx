import React, { useCallback, useContext, useEffect, useState } from "react";
import {
  CommandBar,
  DefaultPalette,
  ICommandBarItemProps,
  SearchBox,
  Stack,
  Text,
  TooltipHost,
  Icon,
  IconButton,
  ContextualMenu,
  IContextualMenuProps,
  IContextualMenuItem,
  DirectionalHint,
  getTheme,
} from "@fluentui/react";
import { Workspace } from "../../models/workspace";
import { ResourceCardList } from "../shared/ResourceCardList";
import { Resource } from "../../models/resource";
import { CostsContext } from "../../contexts/CostsContext";
import moment from "moment";

interface WorkspaceListProps {
  workspaces: Array<Workspace>;
  updateWorkspace: (w: Workspace) => void;
  removeWorkspace: (w: Workspace) => void;
  addWorkspace: (w: Workspace) => void;
}

type SortOption = "name" | "id" | "created" | "cost";

export const WorkspaceList: React.FunctionComponent<WorkspaceListProps> = ({
  workspaces,
  updateWorkspace,
  removeWorkspace,
  addWorkspace,
}) => {
  // State for sorting and filtering
  const [sortBy, setSortBy] = useState<SortOption>("name");
  const [sortAscending, setSortAscending] = useState(true);
  const [searchFilter, setSearchFilter] = useState("");
  const [filteredWorkspaces, setFilteredWorkspaces] = useState<Workspace[]>([]);
  const [contextMenuProps, setContextMenuProps] = useState<IContextualMenuProps>();

  const costsCtx = useContext(CostsContext);
  const theme = getTheme();

  // Load sort preferences from localStorage on mount
  useEffect(() => {
    const savedSortBy = localStorage.getItem("workspace-sort-by") as SortOption;
    const savedSortAscending = localStorage.getItem("workspace-sort-ascending");

    if (savedSortBy) {
      setSortBy(savedSortBy);
    }
    if (savedSortAscending) {
      setSortAscending(savedSortAscending === "true");
    }
  }, []);

  // Save sort preferences to localStorage
  useEffect(() => {
    localStorage.setItem("workspace-sort-by", sortBy);
    localStorage.setItem("workspace-sort-ascending", sortAscending.toString());
  }, [sortBy, sortAscending]);

  // Get workspace cost by ID
  const getWorkspaceCost = useCallback(
    (workspaceId: string): number => {
      const workspaceCost = costsCtx.costs.find((cost) => cost.id === workspaceId);
      if (workspaceCost && workspaceCost.costs.length > 0) {
        // Return the latest cost (assume sorted by date)
        return workspaceCost.costs[workspaceCost.costs.length - 1].cost;
      }
      return 0;
    },
    [costsCtx.costs],
  );

  // Sort workspaces based on current sort criteria
  const sortWorkspaces = useCallback(
    (workspacesToSort: Workspace[]): Workspace[] => {
      const sorted = [...workspacesToSort].sort((a, b) => {
        let comparison = 0;

        switch (sortBy) {
          case "name":
            comparison = (a.properties?.display_name || a.id).localeCompare(
              b.properties?.display_name || b.id,
            );
            break;
          case "id":
            comparison = a.id.localeCompare(b.id);
            break;
          case "created":
            comparison = a.updatedWhen - b.updatedWhen;
            break;
          case "cost":
            comparison = getWorkspaceCost(a.id) - getWorkspaceCost(b.id);
            break;
          default:
            comparison = 0;
        }

        return sortAscending ? comparison : -comparison;
      });

      return sorted;
    },
    [sortBy, sortAscending, getWorkspaceCost],
  );

  // Filter workspaces based on search criteria
  const filterWorkspaces = useCallback(
    (workspacesToFilter: Workspace[]): Workspace[] => {
      if (!searchFilter.trim()) {
        return workspacesToFilter;
      }

      const searchTerm = searchFilter.toLowerCase();
      return workspacesToFilter.filter((workspace) => {
        const displayName = workspace.properties?.display_name?.toLowerCase() || "";
        const workspaceId = workspace.id.toLowerCase();
        return displayName.includes(searchTerm) || workspaceId.includes(searchTerm);
      });
    },
    [searchFilter],
  );

  // Apply filtering and sorting whenever workspaces or criteria change
  useEffect(() => {
    const filtered = filterWorkspaces(workspaces);
    const sorted = sortWorkspaces(filtered);
    setFilteredWorkspaces(sorted);
  }, [workspaces, filterWorkspaces, sortWorkspaces]);

  // Handle sort change
  const handleSortChange = (newSortBy: SortOption) => {
    if (newSortBy === sortBy) {
      setSortAscending(!sortAscending);
    } else {
      setSortBy(newSortBy);
      setSortAscending(true);
    }
  };

  // Create sort menu items
  const sortMenuItems: IContextualMenuItem[] = [
    {
      key: "name",
      text: "Workspace Name",
      iconProps: { iconName: sortBy === "name" ? (sortAscending ? "SortUp" : "SortDown") : "Sort" },
      onClick: () => handleSortChange("name"),
    },
    {
      key: "id",
      text: "Workspace ID",
      iconProps: { iconName: sortBy === "id" ? (sortAscending ? "SortUp" : "SortDown") : "Sort" },
      onClick: () => handleSortChange("id"),
    },
    {
      key: "created",
      text: "Creation Date",
      iconProps: { iconName: sortBy === "created" ? (sortAscending ? "SortUp" : "SortDown") : "Sort" },
      onClick: () => handleSortChange("created"),
    },
    {
      key: "cost",
      text: "Workspace Cost",
      iconProps: { iconName: sortBy === "cost" ? (sortAscending ? "SortUp" : "SortDown") : "Sort" },
      onClick: () => handleSortChange("cost"),
    },
  ];

  // Handle sort button click
  const handleSortButtonClick = (ev?: React.MouseEvent<HTMLElement> | React.KeyboardEvent<HTMLElement>) => {
    if (!ev) return;
    setContextMenuProps({
      items: sortMenuItems,
      target: ev.currentTarget as HTMLElement,
      directionalHint: DirectionalHint.bottomLeftEdge,
      gapSpace: 0,
      onDismiss: () => setContextMenuProps(undefined),
    });
  };

  // Create command bar items
  const commandBarItems: ICommandBarItemProps[] = [
    {
      key: "search",
      onRender: () => (
        <SearchBox
          placeholder="Search workspaces by name or ID..."
          value={searchFilter}
          onChange={(_, newValue) => setSearchFilter(newValue || "")}
          onClear={() => setSearchFilter("")}
          styles={{
            root: { width: 300, marginRight: 10 },
          }}
        />
      ),
    },
  ];

  const farCommandBarItems: ICommandBarItemProps[] = [
    {
      key: "sort",
      text: "Sort",
      iconProps: { iconName: "Sort" },
      onClick: handleSortButtonClick,
    },
    {
      key: "clear-search",
      text: "Clear search",
      iconProps: { iconName: "Clear" },
      disabled: !searchFilter.trim(),
      onClick: () => setSearchFilter(""),
    },
  ];

  return (
    <>
      <Stack>
        <Stack.Item>
          <CommandBar
            items={commandBarItems}
            farItems={farCommandBarItems}
            ariaLabel="Workspace list controls"
          />
        </Stack.Item>
        <Stack.Item>
          {/* Display current sort info */}
          <Stack horizontal verticalAlign="center" tokens={{ childrenGap: 10 }}>
            <Text variant="small" styles={{ root: { color: theme.palette.neutralSecondary } }}>
              Sorted by {sortBy === "name" ? "Workspace Name" : 
                        sortBy === "id" ? "Workspace ID" : 
                        sortBy === "created" ? "Creation Date" : 
                        "Workspace Cost"} 
              ({sortAscending ? "ascending" : "descending"})
            </Text>
            {searchFilter && (
              <Text variant="small" styles={{ root: { color: theme.palette.neutralSecondary } }}>
                • Filtered by "{searchFilter}"
              </Text>
            )}
          </Stack>
        </Stack.Item>
        <Stack.Item>
          <ResourceCardList
            resources={filteredWorkspaces}
            updateResource={(r: Resource) => updateWorkspace(r as Workspace)}
            removeResource={(r: Resource) => removeWorkspace(r as Workspace)}
            emptyText={
              searchFilter
                ? `No workspaces found matching "${searchFilter}". Try a different search term.`
                : "No workspaces to display. Create one to get started."
            }
          />
        </Stack.Item>
      </Stack>
      {contextMenuProps && <ContextualMenu {...contextMenuProps} />}
    </>
  );
};
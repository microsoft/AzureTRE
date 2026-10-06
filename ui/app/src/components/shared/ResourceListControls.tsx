import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  CommandBar,
  ContextualMenu,
  DirectionalHint,
  ICommandBarItemProps,
  IContextualMenuProps,
  SearchBox,
  Stack,
} from "@fluentui/react";
import { Resource } from "../../models/resource";

export interface ResourceSortOption<T extends Resource> {
  key: string;
  text: string;
  compare: (a: T, b: T) => number;
}

const displayName = (r: Resource) => r.properties?.display_name || r.id;
export const resourceStatus = (r: Resource) => r.azureStatus?.powerState || r.deploymentStatus || "";

export const nameSortOption = <T extends Resource>(): ResourceSortOption<T> => ({
  key: "name",
  text: "Name",
  compare: (a, b) => displayName(a).localeCompare(displayName(b), undefined, { numeric: true }),
});

export const statusSortOption = <T extends Resource>(): ResourceSortOption<T> => ({
  key: "status",
  text: "Status",
  compare: (a, b) => resourceStatus(a).localeCompare(resourceStatus(b)),
});

export const updatedSortOption = <T extends Resource>(): ResourceSortOption<T> => ({
  key: "updated",
  text: "Last updated",
  compare: (a, b) => (a.updatedWhen || 0) - (b.updatedWhen || 0),
});

export const defaultSortOptions = <T extends Resource>(): Array<ResourceSortOption<T>> => [
  nameSortOption<T>(),
  statusSortOption<T>(),
  updatedSortOption<T>(),
];

interface ResourceListFilterOptions<T extends Resource> {
  // Prefix for the sort preference saved in localStorage.
  storageKey: string;
  sortOptions: Array<ResourceSortOption<T>>;
  // Extra text to match when searching, for example an owner's name.
  extraSearchText?: (r: T) => Array<string | undefined>;
  // Applied before searching, for example to show only the user's own resources.
  preFilter?: (r: T) => boolean;
}

// Search and sort state for a resource list, shared by all resource lists so they behave the same.
export const useResourceListFilter = <T extends Resource>(
  resources: Array<T>,
  options: ResourceListFilterOptions<T>,
) => {
  const { storageKey, sortOptions, extraSearchText, preFilter } = options;
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState(() => {
    const saved = localStorage.getItem(`${storageKey}-sort-by`);
    return sortOptions.some((o) => o.key === saved) ? (saved as string) : sortOptions[0].key;
  });
  const [sortAscending, setSortAscending] = useState(
    () => localStorage.getItem(`${storageKey}-sort-ascending`) !== "false",
  );

  useEffect(() => {
    localStorage.setItem(`${storageKey}-sort-by`, sortKey);
    localStorage.setItem(`${storageKey}-sort-ascending`, sortAscending.toString());
  }, [storageKey, sortKey, sortAscending]);

  const onSortChange = useCallback(
    (key: string) => {
      if (key === sortKey) {
        setSortAscending((asc) => !asc);
      } else {
        setSortKey(key);
        setSortAscending(true);
      }
    },
    [sortKey],
  );

  const visibleResources = useMemo(() => {
    const term = search.trim().toLowerCase();
    const candidates = preFilter ? resources.filter(preFilter) : resources;
    const matched = term
      ? candidates.filter(
          (r) =>
            // IDs are prefix-matched only: every UUID v4 contains "-4", so substring matching would match everything
            (r.id || "").toLowerCase().startsWith(term) ||
            [
              r.properties?.display_name,
              r.properties?.description,
              r.templateName,
              resourceStatus(r),
              // Status is displayed with spaces (e.g. "deployment failed").
              resourceStatus(r).replace(/_/g, " "),
              ...(extraSearchText ? extraSearchText(r) : []),
            ]
              .filter(Boolean)
              .some((value) => String(value).toLowerCase().includes(term)),
        )
      : candidates;
    const option = sortOptions.find((o) => o.key === sortKey) || sortOptions[0];
    return [...matched].sort((a, b) => (sortAscending ? option.compare(a, b) : -option.compare(a, b)));
  }, [resources, search, sortKey, sortAscending, sortOptions, extraSearchText, preFilter]);

  return {
    visibleResources,
    controlsProps: {
      search,
      onSearchChange: setSearch,
      sortOptions: sortOptions.map(({ key, text }) => ({ key, text })),
      sortKey,
      sortAscending,
      onSortChange,
    },
  };
};

interface ResourceListControlsProps {
  search: string;
  onSearchChange: (search: string) => void;
  sortOptions: Array<{ key: string; text: string }>;
  sortKey: string;
  sortAscending: boolean;
  onSortChange: (key: string) => void;
  searchPlaceholder?: string;
  ariaLabel?: string;
  showMine?: boolean;
  // When set, adds a "Show" menu to switch between the user's own resources and all resources.
  onShowMineChange?: (showMine: boolean) => void;
  // Additional far-right items, for example Refresh on lists without a page header.
  farItems?: Array<ICommandBarItemProps>;
}

export const ResourceListControls: React.FunctionComponent<ResourceListControlsProps> = (props) => {
  const [sortMenu, setSortMenu] = useState<IContextualMenuProps>();
  const sortText = props.sortOptions.find((o) => o.key === props.sortKey)?.text || props.sortKey;

  const farItems: Array<ICommandBarItemProps> = [];
  if (props.onShowMineChange) {
    const onShowMineChange = props.onShowMineChange;
    farItems.push({
      key: "scope",
      text: props.showMine ? "My resources" : "All resources",
      ariaLabel: `Showing ${props.showMine ? "my resources" : "all resources"}. Change view`,
      iconProps: { iconName: props.showMine ? "FilterSolid" : "Filter" },
      subMenuProps: {
        items: [
          {
            key: "mine",
            text: "My resources",
            canCheck: true,
            checked: !!props.showMine,
            onClick: () => onShowMineChange(true),
          },
          {
            key: "all",
            text: "All resources",
            canCheck: true,
            checked: !props.showMine,
            onClick: () => onShowMineChange(false),
          },
        ],
      },
    });
  }
  farItems.push(
    {
      key: "sort",
      text: `Sort: ${sortText} ${props.sortAscending ? "↑" : "↓"}`,
      iconProps: { iconName: "Sort" },
      onClick: (ev) => {
        if (!ev) return;
        setSortMenu({
          items: props.sortOptions.map((o) => ({
            key: o.key,
            text: o.text,
            iconProps: {
              iconName: o.key === props.sortKey ? (props.sortAscending ? "SortUp" : "SortDown") : "Sort",
            },
            onClick: () => props.onSortChange(o.key),
          })),
          target: ev.currentTarget as HTMLElement,
          directionalHint: DirectionalHint.bottomLeftEdge,
          gapSpace: 0,
          onDismiss: () => setSortMenu(undefined),
        });
      },
    },
    {
      key: "clear-search",
      text: "Clear search",
      iconProps: { iconName: "Clear" },
      disabled: !props.search.trim(),
      onClick: () => props.onSearchChange(""),
    },
    ...(props.farItems || []),
  );

  return (
    <>
      {/* SearchBox is kept outside the CommandBar so ResizeGroup re-measuring can't remount it mid-typing */}
      <Stack horizontal verticalAlign="center" wrap tokens={{ childrenGap: 10 }}>
        <SearchBox
          placeholder={props.searchPlaceholder || "Search by name, ID or status..."}
          ariaLabel={props.searchPlaceholder || "Search"}
          value={props.search}
          onChange={(_, value) => props.onSearchChange(value || "")}
          onClear={() => props.onSearchChange("")}
          styles={{ root: { width: 300 } }}
        />
        <Stack.Item grow>
          <CommandBar items={[]} farItems={farItems} ariaLabel={props.ariaLabel || "Resource list controls"} />
        </Stack.Item>
      </Stack>
      {sortMenu && <ContextualMenu {...sortMenu} />}
    </>
  );
};

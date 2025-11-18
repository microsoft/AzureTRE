import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ColumnActionsMode,
  CommandBar,
  CommandBarButton,
  ContextualMenu,
  DirectionalHint,
  getTheme,
  IColumn,
  ICommandBarItemProps,
  Icon,
  IContextualMenuItem,
  IContextualMenuProps,
  Persona,
  PersonaSize,
  SelectionMode,
  ShimmeredDetailsList,
  SearchBox,
  Stack,
} from "@fluentui/react";
import { HttpMethod, useAuthApiCall } from "../../hooks/useAuthApiCall";
import { ApiEndpoint } from "../../models/apiEndpoints";
import {
  AirlockRequest,
  AirlockRequestStatus,
  AirlockRequestType,
} from "../../models/airlock";
import moment from "moment";
import { useNavigate } from "react-router-dom";
import { LoadingState } from "../../models/loadingState";
import { APIError } from "../../models/exceptions";
import { ExceptionLayout } from "./ExceptionLayout";
import { getFileTypeIconProps } from "@fluentui/react-file-type-icons";

interface Workspace {
  id: string;
  properties: {
    display_name: string;
  };
}

export const RequestsList: React.FunctionComponent = () => {
  const [myAirlockRequests, setMyAirlockRequests] = useState(
    [] as AirlockRequest[],
  );
  const [airlockManagerRequests, setAirlockManagerRequests] = useState(
    [] as AirlockRequest[],
  );
  const [airlockRequests, setAirlockRequests] = useState(
    [] as AirlockRequest[],
  );
  const [requestColumns, setRequestColumns] = useState([] as IColumn[]);
  const [orderBy, setOrderBy] = useState("updatedWhen");
  const [orderAscending, setOrderAscending] = useState(false);
  const [filters, setFilters] = useState(new Map<string, string>());
  const [loadingState, setLoadingState] = useState(LoadingState.Loading);
  const [contextMenuProps, setContextMenuProps] =
    useState<IContextualMenuProps>();
  const [apiError, setApiError] = useState<APIError>();
  const [activeFilter, setActiveFilter] = useState<string>("myRequests");
  const [searchText, setSearchText] = useState("");
  const apiCall = useAuthApiCall();
  const theme = getTheme();
  const navigate = useNavigate();

  const mapRequestsToWorkspace = (
    requests: AirlockRequest[],
    workspaces: Workspace[],
  ) => {
    return requests.map((request) => {
      const workspace = workspaces.find((w) => w.id === request.workspaceId);
      return {
        ...request,
        workspace: workspace
          ? workspace.properties.display_name
          : "Unknown Workspace",
      };
    });
  };

  const buildQuery = useCallback(() => {
    const params = new URLSearchParams();
    filters.forEach((value, key) => {
      params.append(key, value);
    });
    if (orderBy) {
      params.append("order_by", orderBy);
      params.append("order_ascending", String(orderAscending));
    }
    const query = params.toString();
    return query ? `?${query}` : "";
  }, [filters, orderBy, orderAscending]);

  const updateDisplayedRequests = useCallback(() => {
    if (activeFilter === "allRequests") {
      setAirlockRequests(airlockManagerRequests);
    } else if (activeFilter === "awaitingMyReview") {
      setAirlockRequests(
        airlockManagerRequests.filter(
          (r) => r.status === AirlockRequestStatus.InReview,
        ),
      );
    } else {
      setAirlockRequests(myAirlockRequests);
    }
  }, [activeFilter, airlockManagerRequests, myAirlockRequests]);

  const getAirlockRequests = useCallback(async () => {
    setApiError(undefined);
    setLoadingState(LoadingState.Loading);
    try {
      const query = buildQuery();
      const workspacePromise = apiCall(ApiEndpoint.Workspaces, HttpMethod.Get);
      const myRequestsPromise = apiCall(
        `${ApiEndpoint.Requests}${query}`,
        HttpMethod.Get,
      );
      const managerRequestsPromise = apiCall(
        `${ApiEndpoint.Requests}${query}${query ? "&" : "?"}airlock_manager=true`,
        HttpMethod.Get,
      );

      const [{ workspaces: fetchedWorkspaces }, myRequests, managerRequests] =
        await Promise.all([
          workspacePromise,
          myRequestsPromise,
          managerRequestsPromise,
        ]);

      const mappedMyRequests = mapRequestsToWorkspace(
        myRequests,
        fetchedWorkspaces || [],
      );
      const mappedManagerRequests = mapRequestsToWorkspace(
        managerRequests,
        fetchedWorkspaces || [],
      );

      setMyAirlockRequests(mappedMyRequests);
      setAirlockManagerRequests(mappedManagerRequests);
      setLoadingState(LoadingState.Ok);
    } catch (err: any) {
      err.userMessage = "Error fetching airlock requests";
      setApiError(err);
      setLoadingState(LoadingState.Error);
    }
  }, [apiCall, buildQuery]);

  useEffect(() => {
    getAirlockRequests();
  }, [getAirlockRequests]);

  useEffect(() => {
    updateDisplayedRequests();
  }, [updateDisplayedRequests]);

  const orderRequests = (column: IColumn) => {
    setOrderBy((o) => {
      if (o === column.key) {
        setOrderAscending((previous) => !previous);
        return column.key;
      }
      return column.key;
    });
  };

  const handleSortChange = (field: string) => {
    setOrderBy((current) => {
      if (current === field) {
        setOrderAscending((prev) => !prev);
        return current;
      }
      setOrderAscending(false);
      return field;
    });
    setContextMenuProps(undefined);
  };

  const sortOptions: { key: string; label: string }[] = [
    { key: "updatedWhen", label: "Last Updated" },
    { key: "createdWhen", label: "Created Date" },
    { key: "title", label: "Title" },
    { key: "status", label: "Status" },
  ];

  const sortMenuItems: IContextualMenuItem[] = sortOptions.map((option) => ({
    key: option.key,
    text: option.label,
    iconProps: {
      iconName:
        orderBy === option.key
          ? orderAscending
            ? "SortUp"
            : "SortDown"
          : "Sort",
    },
    onClick: () => handleSortChange(option.key),
  }));

  const handleSortButtonClick = (
    ev?: React.MouseEvent<HTMLElement> | React.KeyboardEvent<HTMLElement>,
  ) => {
    if (!ev) {
      return;
    }
    setContextMenuProps({
      items: sortMenuItems,
      target: ev.currentTarget as HTMLElement,
      directionalHint: DirectionalHint.bottomLeftEdge,
      gapSpace: 0,
      onDismiss: () => setContextMenuProps(undefined),
    });
  };

  const getSortDisplayText = () => {
    const option = sortOptions.find((opt) => opt.key === orderBy);
    if (!option) {
      return "Sort: Last Updated";
    }
    return `Sort: ${option.label} ${orderAscending ? "↑" : "↓"}`;
  };

  const openContextMenu = useCallback(
    (
      column: IColumn,
      ev: React.MouseEvent<HTMLElement>,
      options: Array<string>,
    ) => {
      const filterOptions = options.map((option) => {
        return {
          key: option,
          name: option,
          canCheck: true,
          checked:
            filters?.has(column.key) && filters.get(column.key) === option,
          onClick: () => {
            setFilters((f) => {
              if (f.get(column.key) === option) {
                f.delete(column.key);
              } else {
                f.set(column.key, option);
              }
              return new Map(f);
            });
          },
        };
      });

      const items: IContextualMenuItem[] = [
        {
          key: "sort",
          name: "Sort",
          iconProps: { iconName: "Sort" },
          onClick: () => orderRequests(column),
        },
        {
          key: "filter",
          name: "Filter",
          iconProps: { iconName: "Filter" },
          subMenuProps: {
            items: filterOptions,
          },
        },
      ];

      setContextMenuProps({
        items: items,
        target: ev.currentTarget as HTMLElement,
        directionalHint: DirectionalHint.bottomCenter,
        gapSpace: 0,
        onDismiss: () => setContextMenuProps(undefined),
      });
    },
    [filters],
  );

  useEffect(() => {
    const orderByColumn = (
      ev: React.MouseEvent<HTMLElement>,
      column: IColumn,
    ) => {
      orderRequests(column);
    };

    const columns: IColumn[] = [
      {
        key: "fileIcon",
        name: "fileIcon",
        minWidth: 16,
        maxWidth: 16,
        isIconOnly: true,
        onRender: (request: AirlockRequest) => {
          if (request.status === AirlockRequestStatus.Draft) {
            return (
              <Icon
                iconName="FolderOpen"
                style={{ verticalAlign: "bottom", fontSize: 14 }}
              />
            );
          } else if (request.files?.length > 0 && request.files[0].name) {
            const fileType = request.files[0].name.split(".").pop();
            return (
              <Icon
                {...getFileTypeIconProps({ extension: fileType })}
                style={{ verticalAlign: "bottom" }}
              />
            );
          } else {
            return (
              <Icon
                iconName="Page"
                style={{ verticalAlign: "bottom", fontSize: 14 }}
              />
            );
          }
        },
      },
      {
        key: "workspace",
        name: "Workspace",
        ariaLabel: "Workspace of the airlock request",
        minWidth: 150,
        maxWidth: 200,
        isResizable: true,
        fieldName: "workspace",
      },
      {
        key: "title",
        name: "Title",
        ariaLabel: "Title of the airlock request",
        minWidth: 150,
        maxWidth: 300,
        isResizable: true,
        fieldName: "title",
      },
      {
        key: "createdBy",
        name: "Creator",
        ariaLabel: "Creator of the airlock request",
        minWidth: 150,
        maxWidth: 200,
        isResizable: true,
        onRender: (request: AirlockRequest) => (
          <Persona size={PersonaSize.size24} text={request.createdBy?.name} />
        ),
      },
      {
        key: "type",
        name: "Type",
        ariaLabel: "Whether the request is import or export",
        minWidth: 70,
        maxWidth: 100,
        isResizable: true,
        fieldName: "type",
        columnActionsMode: ColumnActionsMode.hasDropdown,
        isSorted: orderBy === "type",
        isSortedDescending: !orderAscending,
        onColumnClick: (ev, column) =>
          openContextMenu(column, ev, Object.values(AirlockRequestType)),
        onColumnContextMenu: (column, ev) =>
          column &&
          ev &&
          openContextMenu(column, ev, Object.values(AirlockRequestType)),
        isFiltered: filters.has("type"),
      },
      {
        key: "status",
        name: "Status",
        ariaLabel: "Status of the request",
        minWidth: 70,
        isResizable: true,
        fieldName: "status",
        columnActionsMode: ColumnActionsMode.hasDropdown,
        isSorted: orderBy === "status",
        isSortedDescending: !orderAscending,
        onColumnClick: (ev, column) =>
          openContextMenu(column, ev, Object.values(AirlockRequestStatus)),
        onColumnContextMenu: (column, ev) =>
          column &&
          ev &&
          openContextMenu(column, ev, Object.values(AirlockRequestStatus)),
        isFiltered: filters.has("status"),
        onRender: (request: AirlockRequest) => request.status.replace("_", " "),
      },
      {
        key: "createdTime",
        name: "Created",
        ariaLabel: "When the request was created",
        minWidth: 120,
        data: "number",
        isResizable: true,
        fieldName: "createdTime",
        isSorted: orderBy === "createdTime",
        isSortedDescending: !orderAscending,
        onRender: (request: AirlockRequest) => {
          return (
            <span>{moment.unix(request.createdWhen).format("DD/MM/YYYY")}</span>
          );
        },
        onColumnClick: orderByColumn,
      },
      {
        key: "updatedWhen",
        name: "Updated",
        ariaLabel: "When the request was last updated",
        minWidth: 120,
        data: "number",
        isResizable: true,
        fieldName: "updatedWhen",
        isSorted: orderBy === "updatedWhen",
        isSortedDescending: !orderAscending,
        onRender: (request: AirlockRequest) => {
          return <span>{moment.unix(request.updatedWhen).fromNow()}</span>;
        },
        onColumnClick: orderByColumn,
      },
    ];
    setRequestColumns(columns);
  }, [openContextMenu, filters, orderAscending, orderBy]);

  const quickFilters: ICommandBarItemProps[] = [];

  if (airlockManagerRequests.length > 0) {
    quickFilters.unshift({
      key: "allRequests",
      text: "All Requests",
      iconProps: {
        iconName: activeFilter === "allRequests" ? "CheckMark" : "BulletedList",
      },
      buttonStyles:
        activeFilter === "allRequests"
          ? {
            root: { fontWeight: "600" },
            label: { fontWeight: "600" },
          }
          : undefined,
      onClick: () => {
        setActiveFilter("allRequests");
        if (filters.size > 0) {
          setFilters(new Map());
        }
        setAirlockRequests(airlockManagerRequests);
      },
    });

    quickFilters.unshift({
      key: "awaitingMyReview",
      text: "Awaiting my review",
      iconProps: {
        iconName:
          activeFilter === "awaitingMyReview" ? "CheckMark" : "TemporaryUser",
      },
      buttonStyles:
        activeFilter === "awaitingMyReview"
          ? {
            root: { fontWeight: "600" },
            label: { fontWeight: "600" },
          }
          : undefined,
      onClick: () => {
        setActiveFilter("awaitingMyReview");
        if (filters.size > 0) {
          setFilters(new Map());
        }
        setAirlockRequests(
          airlockManagerRequests.filter(
            (r) => r.status === AirlockRequestStatus.InReview,
          ),
        );
      },
    });
  }

  quickFilters.unshift({
    key: "myRequests",
    text: "My Requests",
    iconProps: { iconName: activeFilter === "myRequests" ? "CheckMark" : "EditContact" },
    buttonStyles: activeFilter === "myRequests" ? {
      root: { fontWeight: '600' },
      label: { fontWeight: '600' }
    } : undefined,
    onClick: () => {
      setActiveFilter("myRequests");
      if (filters.size > 0) {
        setFilters(new Map());
      }
      setAirlockRequests(myAirlockRequests);
    },
  });

  const filteredRequests = useMemo(() => {
    const term = searchText.trim().toLowerCase();
    if (!term) {
      return airlockRequests;
    }
    return airlockRequests.filter((request) => {
      const candidates = [
        request.workspace,
        request.title,
        request.createdBy?.name,
        request.createdBy?.email,
        request.status,
        request.type,
      ]
        .filter(Boolean)
        .map((value) => value!.toString().toLowerCase());
      return candidates.some((value) => value.includes(term));
    });
  }, [airlockRequests, searchText]);

  const quickFilterCommandBarItems: ICommandBarItemProps[] = quickFilters;

  const searchCommandBarItems: ICommandBarItemProps[] = [
    {
      key: "search",
      onRender: () => (
        <SearchBox
          placeholder="Search requests..."
          value={searchText}
          onChange={(_, newValue) => setSearchText(newValue || "")}
          onClear={() => setSearchText("")}
          styles={{ root: { width: 320 } }}
        />
      ),
    },
  ];

  const searchCommandBarFarItems: ICommandBarItemProps[] = [
    {
      key: "sort",
      text: getSortDisplayText(),
      iconProps: { iconName: "Sort" },
      onClick: handleSortButtonClick,
    },
    {
      key: "clear-search",
      text: "Clear search",
      iconProps: { iconName: "Clear" },
      disabled: searchText.trim().length === 0,
      onClick: () => setSearchText(""),
    },
  ];

  return (
    <>
      <Stack className="tre-panel">
        <Stack.Item>
          <Stack tokens={{ childrenGap: 12 }}>
            <Stack
              horizontal
              horizontalAlign="space-between"
              verticalAlign="center"
            >
              <h1 style={{ marginBottom: 0 }}>Airlock Requests</h1>
              <CommandBarButton
                iconProps={{ iconName: "refresh" }}
                text="Refresh"
                style={{ background: "none", color: theme.palette.themePrimary }}
                onClick={() => {
                  getAirlockRequests();
                }}
              />
            </Stack>
            <CommandBar
              items={quickFilterCommandBarItems}
              ariaLabel="Quick filters"
            />
            <CommandBar
              items={searchCommandBarItems}
              farItems={searchCommandBarFarItems}
              ariaLabel="Search and sort controls"
            />
          </Stack>
        </Stack.Item>
      </Stack>
      {apiError && <ExceptionLayout e={apiError} />}
      <div className="tre-resource-panel" style={{ padding: "0px" }}>
        <ShimmeredDetailsList
          items={filteredRequests}
          columns={requestColumns}
          selectionMode={SelectionMode.none}
          getKey={(item) => item?.id}
          onItemInvoked={(item) =>
            navigate(
              `/${ApiEndpoint.Workspaces}/${item.workspaceId}/${ApiEndpoint.AirlockRequests}/${item.id}`,
            )
          }
          className="tre-table"
          enableShimmer={loadingState === LoadingState.Loading}
        />
        {contextMenuProps && <ContextualMenu {...contextMenuProps} />}
        {filteredRequests.length === 0 &&
          loadingState !== LoadingState.Loading && (
            <div
              style={{ textAlign: "center", padding: "50px 10px 100px 10px" }}
            >
              <h4>No requests found</h4>
              {filters.size > 0 || searchText.trim().length > 0 ? (
                <small>
                  There are no requests matching your selected filter(s).
                </small>
              ) : (
                <small>
                  Looks like there are no airlock requests yet. Create a new
                  request to get started.
                </small>
              )}
            </div>
          )}
      </div>
    </>
  );
};

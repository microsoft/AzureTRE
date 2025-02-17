import React, { useCallback, useEffect, useState } from "react";
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

  const getAirlockRequests = useCallback(async () => {
    setApiError(undefined);
    setLoadingState(LoadingState.Loading);
    try {
      let query = "?";
      filters.forEach((value, key) => {
        query += `${key}=${value}&`;
      });
      if (orderBy) {
        query += `order_by=${orderBy}&order_ascending=${orderAscending}&`;
      }
      let fetchedWorkspaces: { workspaces: Workspace[] } = { workspaces: [] };
      try {
        fetchedWorkspaces = await apiCall(
          ApiEndpoint.Workspaces,
          HttpMethod.Get,
        );
      } catch (err: any) {
        setApiError(err);
        console.error("Failed to fetch workspaces:", err);
      }
      let requests: AirlockRequest[];
      let airlock_manager_requests: AirlockRequest[];
      requests = await apiCall(
        `${ApiEndpoint.Requests}${query.slice(0, -1)}`,
        HttpMethod.Get,
      );
      requests = mapRequestsToWorkspace(requests, fetchedWorkspaces.workspaces);
      airlock_manager_requests = await apiCall(
        `${ApiEndpoint.Requests}?${query.slice(0, -1)}&airlock_manager=true`,
        HttpMethod.Get,
      );
      airlock_manager_requests = mapRequestsToWorkspace(
        airlock_manager_requests,
        fetchedWorkspaces.workspaces,
      );

      setMyAirlockRequests(requests);
      setAirlockRequests(requests);
      setLoadingState(LoadingState.Ok);
      setAirlockManagerRequests(airlock_manager_requests);
    } catch (err: any) {
      err.userMessage = "Error fetching airlock requests";
      setApiError(err);
      setLoadingState(LoadingState.Error);
    }
  }, [filters, orderBy, apiCall, orderAscending]);

  useEffect(() => {
    getAirlockRequests();
  }, [filters, orderBy, orderAscending, getAirlockRequests]);

  const orderRequests = (column: IColumn) => {
    setOrderBy((o) => {
      if (o === column.key) {
        setOrderAscending((previous) => !previous);
        return column.key;
      }
      return column.key;
    });
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
        isFiltered: filters.has("creator_user_id"),
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

  const quickFilters: ICommandBarItemProps[] = [
    {
      key: "reset",
      text: "Clear filters",
      iconProps: { iconName: "ClearFilter" },
      onClick: () => setFilters(new Map()),
    },
  ];

  if (airlockManagerRequests.length > 0) {
    quickFilters.unshift({
      key: "allRequests",
      text: "All Requests",
      iconProps: { iconName: "BulletedList" },
      onClick: () => {
        setFilters(new Map());
        setAirlockRequests(airlockManagerRequests);
      },
    });

    quickFilters.unshift({
      key: "awaitingMyReview",
      text: "Awaiting my review",
      iconProps: { iconName: "TemporaryUser" },
      onClick: () => {
        setFilters(new Map([["status", "in_review"]]));
        setAirlockRequests(airlockManagerRequests);
      },
    });
  }

  quickFilters.unshift({
    key: "myRequests",
    text: "My Requests",
    iconProps: { iconName: "EditContact" },
    onClick: () => {
      setFilters(new Map());
      setAirlockRequests(myAirlockRequests);
    },
  });

  return (
    <>
      <Stack className="tre-panel">
        <Stack.Item>
          <Stack horizontal horizontalAlign="space-between">
            <h1 style={{ marginBottom: 0, marginRight: 30 }}>
              Airlock Requests
            </h1>
            <Stack.Item grow>
              <CommandBar items={quickFilters} ariaLabel="Quick filters" />
            </Stack.Item>
            <CommandBarButton
              iconProps={{ iconName: "refresh" }}
              text="Refresh"
              style={{ background: "none", color: theme.palette.themePrimary }}
              onClick={() => getAirlockRequests()}
            />
          </Stack>
        </Stack.Item>
      </Stack>
      {apiError && <ExceptionLayout e={apiError} />}
      <div className="tre-resource-panel" style={{ padding: "0px" }}>
        <ShimmeredDetailsList
          items={airlockRequests}
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
        {airlockRequests.length === 0 &&
          loadingState !== LoadingState.Loading && (
            <div
              style={{ textAlign: "center", padding: "50px 10px 100px 10px" }}
            >
              <h4>No requests found</h4>
              {filters.size > 0 ? (
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

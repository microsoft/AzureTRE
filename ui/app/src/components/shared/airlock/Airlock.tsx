import React, { useCallback, useContext, useEffect, useState } from 'react';
import { ColumnActionsMode, CommandBar, CommandBarButton, ContextualMenu, DirectionalHint, getTheme, IColumn, ICommandBarItemProps, Icon, IContextualMenuItem, IContextualMenuProps, Persona, PersonaSize, SelectionMode, ShimmeredDetailsList, Stack } from '@fluentui/react';
import { HttpMethod, useAuthApiCall } from '../../../hooks/useAuthApiCall';
import { ApiEndpoint } from '../../../models/apiEndpoints';
import { WorkspaceContext } from '../../../contexts/WorkspaceContext';
import { AirlockRequest, AirlockRequestAction, AirlockRequestStatus, AirlockRequestType } from '../../../models/airlock';
import moment from 'moment';
import { Route, Routes, useNavigate } from 'react-router-dom';
import { AirlockViewRequest } from './AirlockViewRequest';
import { LoadingState } from '../../../models/loadingState';
import { APIError } from '../../../models/exceptions';
import { ExceptionLayout } from '../ExceptionLayout';
import { AirlockNewRequest } from './AirlockNewRequest';
import { WorkspaceRoleName } from '../../../models/roleNames';
import { useAccount, useMsal } from '@azure/msal-react';
import { getFileTypeIconProps } from '@fluentui/react-file-type-icons';

export const Airlock: React.FunctionComponent = () => {
  const [airlockRequests, setAirlockRequests] = useState([] as AirlockRequest[]);
  const [requestColumns, setRequestColumns] = useState([] as IColumn[]);
  const [orderBy, setOrderBy] = useState('updatedWhen');
  const [orderAscending, setOrderAscending] = useState(false);
  const [filters, setFilters] = useState(new Map<string, string>());
  const [loadingState, setLoadingState] = useState(LoadingState.Loading);
  const [contextMenuProps, setContextMenuProps] = useState<IContextualMenuProps>();
  const [apiError, setApiError] = useState<APIError>();
  const workspaceCtx = useContext(WorkspaceContext);
  const apiCall = useAuthApiCall();
  const theme = getTheme();
  const navigate = useNavigate();
  const { accounts } = useMsal();
  const account = useAccount(accounts[0] || {});

  // Get the airlock request data from API
  const getAirlockRequests = useCallback(async () => {
    setApiError(undefined);
    setLoadingState(LoadingState.Loading);

    try {
      let requests: AirlockRequest[];
      if (workspaceCtx.workspace) {

        // Add any selected filters and orderBy
        let query = '?';
        filters.forEach((value, key) => {
          query += `${key}=${value}&`;
        });
        if (orderBy) {
          query += `order_by=${orderBy}&order_ascending=${orderAscending}&`;
        }

        // Call the Airlock requests API
        const result = await apiCall(
          `${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.AirlockRequests}${query.slice(0, -1)}`,
          HttpMethod.Get,
          workspaceCtx.workspaceApplicationIdURI
        );

        // Map the inner requests and the allowed user actions to state
        requests = result.airlockRequests.map((r: {
          airlockRequest: AirlockRequest,
          allowedUserActions: Array<AirlockRequestAction>
        }) => {
          const request = r.airlockRequest;
          request.allowedUserActions = r.allowedUserActions;
          return request;
        });
      } else {
        // TODO: Get all requests across workspaces
        requests = [];
      }

      setAirlockRequests(requests);
      setLoadingState(LoadingState.Ok);
    } catch (err: any) {
      err.userMessage = 'Error fetching airlock requests';
      setApiError(err);
      setLoadingState(LoadingState.Error);
    }
  }, [apiCall, workspaceCtx.workspace, workspaceCtx.workspaceApplicationIdURI, filters, orderBy, orderAscending]);

  // Fetch new requests on first load and whenever filters/orderBy selection changes
  useEffect(() => {
    getAirlockRequests();
  }, [filters, orderBy, orderAscending, getAirlockRequests]);

  const orderRequests = (column: IColumn) => {
    setOrderBy((o) => {
      // If already selected, invert ordering
      if (o === column.key) {
        setOrderAscending((previous) => !previous);
        return column.key;
      }
      return column.key;
    });
  };

  // Open a context menu in the requests list for filtering and sorting
  const openContextMenu = useCallback((column: IColumn, ev: React.MouseEvent<HTMLElement>, options: Array<string>) => {
    const filterOptions = options.map(option => {
      return {
        key: option,
        name: option,
        canCheck: true,
        checked: filters?.has(column.key) && filters.get(column.key) === option,
        onClick: () => {
          // Set filter or unset if already selected
          setFilters((f) => {
            if (f.get(column.key) === option) {
              f.delete(column.key);
            } else {
              f.set(column.key, option);
            }
            // Return as a new map to trigger re-rendering
            return new Map(f);
          });
        }
      }
    });

    const items: IContextualMenuItem[] = [
      {
          key: 'sort',
          name: 'Sort',
          iconProps: { iconName: 'Sort' },
          onClick: () => orderRequests(column)
      },
      {
        key: 'filter',
        name: 'Filter',
        iconProps: { iconName: 'Filter' },
        subMenuProps: {
          items: filterOptions,
        }
      }
    ];

    setContextMenuProps({
        items: items,
        target: ev.currentTarget as HTMLElement,
        directionalHint: DirectionalHint.bottomCenter,
        gapSpace: 0,
        onDismiss: () => setContextMenuProps(undefined),
    });
  }, [filters]);

  // Set the columns on initial render
  useEffect(() => {
    const orderByColumn = (ev: React.MouseEvent<HTMLElement>, column: IColumn) => {
      orderRequests(column);
    };

    const columns: IColumn[] = [
      {
        key: 'fileIcon',
        name: 'fileIcon',
        minWidth: 16,
        maxWidth: 16,
        isIconOnly: true,
        onRender: (request: AirlockRequest) => {
          if (request.status === AirlockRequestStatus.Draft) {
            return <Icon iconName="FolderOpen" style={{verticalAlign:'bottom', fontSize: 14}} />
          } else if (request.files?.length > 0 && request.files[0].name) {
            const fileType = request.files[0].name.split('.').pop();
            return <Icon {...getFileTypeIconProps({ extension: fileType })} style={{verticalAlign:'bottom'}} />
          } else {
            return <Icon iconName="Page" style={{verticalAlign:'bottom', fontSize: 14}} />
          }
        }
      },
      {
        key: 'title',
        name: 'Title',
        ariaLabel: 'Title of the airlock request',
        minWidth: 150,
        maxWidth: 300,
        isResizable: true,
        fieldName: 'title'
      },
      {
        key: 'createdBy',
        name: 'Creator',
        ariaLabel: 'Creator of the airlock request',
        minWidth: 150,
        maxWidth: 200,
        isResizable: true,
        onRender: (request: AirlockRequest) => <Persona size={ PersonaSize.size24 } text={request.createdBy?.name} />,
        isFiltered: filters.has('creator_user_id')
      },
      {
        key: 'type',
        name: 'Type',
        ariaLabel: 'Whether the request is import or export',
        minWidth: 70,
        maxWidth: 100,
        isResizable: true,
        fieldName: 'type',
        columnActionsMode: ColumnActionsMode.hasDropdown,
        isSorted: orderBy === 'type',
        isSortedDescending: !orderAscending,
        onColumnClick: (ev, column) => openContextMenu(column, ev, Object.values(AirlockRequestType)),
        onColumnContextMenu: (column, ev) =>
          (column && ev) && openContextMenu(column, ev, Object.values(AirlockRequestType)),
        isFiltered: filters.has('type')
      },
      {
        key: 'status',
        name: 'Status',
        ariaLabel: 'Status of the request',
        minWidth: 70,
        isResizable: true,
        fieldName: 'status',
        columnActionsMode: ColumnActionsMode.hasDropdown,
        isSorted: orderBy === 'status',
        isSortedDescending: !orderAscending,
        onColumnClick: (ev, column) => openContextMenu(column, ev, Object.values(AirlockRequestStatus)),
        onColumnContextMenu: (column, ev) =>
          (column && ev) && openContextMenu(column, ev, Object.values(AirlockRequestStatus)),
        isFiltered: filters.has('status'),
        onRender: (request: AirlockRequest) => request.status.replace("_", " ")
      },
      {
        key: 'createdTime',
        name: 'Created',
        ariaLabel: 'When the request was created',
        minWidth: 120,
        data: 'number',
        isResizable: true,
        fieldName: 'createdTime',
        isSorted: orderBy === 'createdTime',
        isSortedDescending: !orderAscending,
        onRender: (request: AirlockRequest) => {
          return <span>{ moment.unix(request.createdWhen).format('DD/MM/YYYY') }</span>;
        },
        onColumnClick: orderByColumn
      },
      {
        key: 'updatedWhen',
        name: 'Updated',
        ariaLabel: 'When the request was last updated',
        minWidth: 120,
        data: 'number',
        isResizable: true,
        fieldName: 'updatedWhen',
        isSorted: orderBy === 'updatedWhen',
        isSortedDescending: !orderAscending,
        onRender: (request: AirlockRequest) => {
          return <span>{ moment.unix(request.updatedWhen).fromNow() }</span>;
        },
        onColumnClick: orderByColumn
      }
    ];
    setRequestColumns(columns);
  }, [openContextMenu, filters, orderAscending, orderBy]);

  const handleNewRequest = async (newRequest: AirlockRequest) => {
    await getAirlockRequests();
    navigate(newRequest.id);
  };

  const quickFilters: ICommandBarItemProps[] = [
    {
      key: 'reset',
      text: 'Clear filters',
      iconProps: { iconName: 'ClearFilter' },
      onClick: () => setFilters(new Map())
    }
  ];

  // If we can access the user's msal account, give option to filter by their user id
  if (account) {
    quickFilters.unshift({
      key: 'myRequests',
      text: 'My requests',
      iconProps: { iconName: 'EditContact' },
      onClick: () => {
        const userId = account.localAccountId.split('.')[0];
        setFilters(new Map([['creator_user_id', userId]]));
      }
    });
  }

  // Only show "Awaiting my review" filter if user in airlock manager role
  if (workspaceCtx.roles?.includes(WorkspaceRoleName.AirlockManager)) {
    quickFilters.unshift({
      key: 'awaitingMyReview',
      text: 'Awaiting my review',
      iconProps: { iconName: 'TemporaryUser' },
      // Currently we don't have assigned reviewers so this will be all requests in review status
      onClick: () => setFilters(new Map([['status', 'in_review']]))
    });
  }

  return (
    <>
      <Stack className="tre-panel">
        <Stack.Item>
          <Stack horizontal horizontalAlign="space-between">
            <h1 style={{marginBottom: 0, marginRight: 30}}>Airlock</h1>
            <Stack.Item grow>
              <CommandBar items={quickFilters} ariaLabel="Quick filters" />
            </Stack.Item>
            <CommandBarButton
              iconProps={{ iconName: 'refresh' }}
              text="Refresh"
              style={{ background: 'none', color: theme.palette.themePrimary }}
              onClick={() => getAirlockRequests()}
            />
            <CommandBarButton
              iconProps={{ iconName: 'add' }}
              text="New request"
              style={{ background: 'none', color: theme.palette.themePrimary }}
              onClick={() => navigate('new')}
            />
          </Stack>
        </Stack.Item>
      </Stack>
      {
        apiError && <ExceptionLayout e={apiError} />
      }
      <div className="tre-resource-panel" style={{padding: '0px'}}>
        <ShimmeredDetailsList
          items={airlockRequests}
          columns={requestColumns}
          selectionMode={SelectionMode.none}
          getKey={(item) => item?.id}
          onItemInvoked={(item) => navigate(item.id)}
          className="tre-table"
          enableShimmer={loadingState === LoadingState.Loading}
        />
        {
          contextMenuProps && <ContextualMenu {...contextMenuProps}/>
        }
        {
          airlockRequests.length === 0 && loadingState !== LoadingState.Loading && <div style={{textAlign: 'center', padding: '50px 10px 100px 10px'}}>
            <h4>No requests found</h4>
            {
              filters.size > 0
                ? <small>There are no requests matching your selected filter(s).</small>
                : <small>Looks like there are no airlock requests yet. Create a new request to get started.</small>
            }
          </div>
        }
      </div>

      <Routes>
        <Route path="new" element={
          <AirlockNewRequest onCreateRequest={handleNewRequest}/>
        } />
        <Route path=":requestId" element={
          <AirlockViewRequest requests={airlockRequests} onUpdateRequest={getAirlockRequests}/>
        } />
      </Routes>
    </>
  );
};


import React, { useContext, useEffect, useState } from 'react';
import { CommandBarButton, DetailsList, getTheme, IColumn, Persona, PersonaSize, SelectionMode, Spinner, SpinnerSize, Stack } from '@fluentui/react';
import { HttpMethod, useAuthApiCall } from '../../../hooks/useAuthApiCall';
import { ApiEndpoint } from '../../../models/apiEndpoints';
import { WorkspaceContext } from '../../../contexts/WorkspaceContext';
import { AirlockRequest } from '../../../models/airlock';
import moment from 'moment';
import { Route, Routes, useNavigate } from 'react-router-dom';
import { AirlockViewRequest } from './AirlockViewRequest';
import { LoadingState } from '../../../models/loadingState';
import { APIError } from '../../../models/exceptions';
import { ExceptionLayout } from '../ExceptionLayout';

interface AirlockProps {
}

export const Airlock: React.FunctionComponent<AirlockProps> = (props: AirlockProps) => {
  const [airlockRequests, setAirlockRequests] = useState([] as AirlockRequest[]);
  const [requestColumns, setRequestColumns] = useState([] as IColumn[]);
  const [loadingState, setLoadingState] = useState(LoadingState.Loading);
  const workspaceCtx = useContext(WorkspaceContext);
  const apiCall = useAuthApiCall();
  const [apiError, setApiError] = useState({} as APIError);
  const theme = getTheme();
  const navigate = useNavigate();

  useEffect(() => {
    const getAirlockRequests = async () => {
      let requests: AirlockRequest[];

      try {
        if (workspaceCtx.workspace) {
          const result = await apiCall(
            `${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.AirlockRequests}`,
            HttpMethod.Get,
            workspaceCtx.workspaceApplicationIdURI
          );
          requests = result.airlockRequests.map((r: { airlockRequest: AirlockRequest }) => r.airlockRequest);
        } else {
          // TODO: Get all requests across workspaces
          requests = [];
        }
        // Order by updatedWhen for initial view
        requests.sort((a, b) => a.updatedWhen < b.updatedWhen ? 1 : -1);
        setAirlockRequests(requests);
        setLoadingState(LoadingState.Ok);
      } catch (err: any) {
        err.userMessage = 'Error fetching airlock requests';
        setApiError(err);
        setLoadingState(LoadingState.Error);
      }
    }
    getAirlockRequests();
  }, [apiCall, workspaceCtx.workspace, workspaceCtx.workspaceApplicationIdURI]);

  useEffect(() => {
    const reorderColumn = (ev: React.MouseEvent<HTMLElement>, column: IColumn): void => {
      // Reset sorting on other columns and invert selected column if already sorted asc/desc
      setRequestColumns(columns => {
        const orderedColumns: IColumn[] = columns.slice();
        const selectedColumn: IColumn = orderedColumns.filter(selCol => column.key === selCol.key)[0];
        orderedColumns.forEach((newCol: IColumn) => {
          if (newCol === selectedColumn) {
            selectedColumn.isSortedDescending = !selectedColumn.isSortedDescending;
            selectedColumn.isSorted = true;
          } else {
            newCol.isSorted = false;
            newCol.isSortedDescending = true;
          }
        });
        return orderedColumns;
      });

      // Re-order airlock requests
      setAirlockRequests(requests => {
        const key = column.fieldName! as keyof AirlockRequest;
        return requests
          .slice(0)
          .sort((a: AirlockRequest, b: AirlockRequest) => (
            (column.isSortedDescending ? a[key] < b[key] : a[key] > b[key]) ? 1 : -1)
          );
        })
    };

    const columns: IColumn[] = [
      {
        key: 'avatar',
        name: '',
        minWidth: 16,
        maxWidth: 16,
        isIconOnly: true,
        onRender: (request: AirlockRequest) => {
          return <Persona size={ PersonaSize.size24 } text={ request.user?.name } />
        }
      },
      {
        key: 'initiator',
        name: 'Initiator',
        ariaLabel: 'Creator of the airlock request',
        minWidth: 150,
        maxWidth: 200,
        isResizable: true,
        onRender: (request: AirlockRequest) => request.user?.name,
        onColumnClick: reorderColumn
      },
      {
        key: 'type',
        name: 'Type',
        ariaLabel: 'Whether the request is import or export',
        minWidth: 70,
        maxWidth: 100,
        isResizable: true,
        fieldName: 'requestType',
        onColumnClick: reorderColumn
      },
      {
        key: 'status',
        name: 'Status',
        ariaLabel: 'Status of the request',
        minWidth: 70,
        isResizable: true,
        fieldName: 'status',
        onColumnClick: reorderColumn
      },
      {
        key: 'created',
        name: 'Created',
        ariaLabel: 'When the request was created',
        minWidth: 120,
        data: 'number',
        isResizable: true,
        fieldName: 'createdTime',
        onRender: (request: AirlockRequest) => {
          return <span>{ moment.unix(request.creationTime).format('DD/MM/YYYY') }</span>;
        },
        onColumnClick: reorderColumn
      },
      {
        key: 'updated',
        name: 'Updated',
        ariaLabel: 'When the request was last updated',
        minWidth: 120,
        data: 'number',
        isResizable: true,
        isSorted: true,
        fieldName: 'updatedWhen',
        onRender: (request: AirlockRequest) => {
          return <span>{ moment.unix(request.updatedWhen).fromNow() }</span>;
        },
        onColumnClick: reorderColumn
      }
    ];
    setRequestColumns(columns);
  }, []);

  let requestsList;
  switch (loadingState) {
    case LoadingState.Ok:
      if (airlockRequests.length > 0) {
        requestsList = (
          <DetailsList
            items={airlockRequests}
            columns={requestColumns}
            selectionMode={SelectionMode.none}
            getKey={(item) => item.id}
            onItemInvoked={(item) => navigate(item.id)}
            className="tre-table-rows-align-centre"
          />
        );
      } else {
        requestsList = (
          <div style={{textAlign: 'center', padding: '50px'}}>
            <h4>No requests found</h4>
            <small>Looks like there are no airlock requests yet. Create a new request to get started.</small>
          </div>
        )
      }
      break;
    case LoadingState.Error:
      requestsList = (
        <ExceptionLayout e={apiError} />
      ); break;
    default:
      requestsList = (
        <div style={{ padding: '50px' }}>
          <Spinner label="Loading airlock requests" ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
        </div>
      ); break;
  }

  const updateRequest = (updatedRequest: AirlockRequest) => {
    setAirlockRequests(requests => {
      const i = requests.findIndex(r => r.id === updatedRequest.id);
      const updatedRequests = [...requests];
      updatedRequests[i] = updatedRequest;
      return updatedRequests;
    });
  };

  return (
    <>
      <Stack className="tre-panel">
        <Stack.Item>
          <Stack horizontal horizontalAlign="space-between">
            <h1 style={{marginBottom: '0px'}}>Airlock</h1>
            <CommandBarButton
              iconProps={{ iconName: 'add' }}
              text="New request"
              style={{ background: 'none', color: theme.palette.themePrimary }}
            />
          </Stack>
        </Stack.Item>
      </Stack>

      <div className="tre-resource-panel" style={{padding: '0px'}}>
        { requestsList }
      </div>

      <Routes>
        <Route path=":requestId" element={
          <AirlockViewRequest requests={airlockRequests} updateRequest={updateRequest}/>
        } />
      </Routes>
    </>
  );

};


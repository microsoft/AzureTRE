import React, { useContext, useEffect, useState } from 'react';
import { CommandBarButton, DetailsList, getTheme, IColumn, IDetailsRowStyles, MessageBar, MessageBarType, Persona, PersonaSize, PrimaryButton, SelectionMode, Spinner, SpinnerSize, Stack } from '@fluentui/react';
import { HttpMethod, useAuthApiCall } from '../../../hooks/useAuthApiCall';
import { ApiEndpoint } from '../../../models/apiEndpoints';
import { Workspace } from '../../../models/workspace';
import { WorkspaceContext } from '../../../contexts/WorkspaceContext';
import { AirlockRequest } from '../../../models/airlock';
import moment from 'moment';

interface AirlockProps {
}

export const Airlock: React.FunctionComponent<AirlockProps> = (props: AirlockProps) => {
  const [airlockRequests, setAirlockRequests] = useState([] as Array<AirlockRequest>);
  const [loadingState, setLoadingState] = useState('loading');
  const workspaceCtx = useContext(WorkspaceContext);
  const apiCall = useAuthApiCall();
  const theme = getTheme();

  useEffect(() => {
    const getAirlockRequests = async () => {
      let requests;

      try {
        if (workspaceCtx.workspace) {
          const result = await apiCall(
            `${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.AirlockRequests}`,
            HttpMethod.Get,
            workspaceCtx.workspaceApplicationIdURI
          );
          requests = result.airlockRequests;
        } else {
          // Get all requests across workspaces
        }
        setAirlockRequests(requests);
        setLoadingState('ok');
      } catch (error) {
        setLoadingState('error');
      }
    }
    getAirlockRequests();
  }, [apiCall]);

  const columns: IColumn[] = [
    {
      key: 'avatar',
      name: '',
      minWidth: 16,
      maxWidth: 16,
      isIconOnly: true,
      onRender: (request: AirlockRequest) => {
        return <Persona size={ PersonaSize.size24 } text={ request.user.name } />
      }
    },
    {
      key: 'initiator',
      name: 'Initiator',
      ariaLabel: 'Creator of the airlock request',
      minWidth: 150,
      maxWidth: 200,
      isResizable: true,
      onRender: (request: AirlockRequest) => request.user.name
    },
    {
      key: 'type',
      name: 'Type',
      ariaLabel: 'Whether the request is import or export',
      minWidth: 70,
      maxWidth: 100,
      isResizable: true,
      fieldName: 'requestType'
    },
    {
      key: 'status',
      name: 'Status',
      ariaLabel: 'Status of the request',
      minWidth: 70,
      isResizable: true,
      fieldName: 'status'
    },
    {
      key: 'updated',
      name: 'Updated',
      ariaLabel: 'When the request was last updated',
      minWidth: 120,
      data: 'number',
      isResizable: true,
      onRender: (request: AirlockRequest) => {
        return <span>{ moment.unix(request.updatedWhen).fromNow() }</span>;
      }
    }
  ];

  let requestsList;
  switch (loadingState) {
    case 'ok':
      requestsList = (
        <DetailsList
          items={airlockRequests}
          columns={columns}
          selectionMode={SelectionMode.none}
          getKey={(item) => item.id}
          onItemInvoked={() => console.log('Item pressed')}
          className="tre-table-rows-align-centre"
        />
      ); break;
    case 'error':
      requestsList = (
        <MessageBar
          messageBarType={MessageBarType.error}
          isMultiline={true}
        >
          <h3>Error fetching airlock requests</h3>
          <p>There was an error fetching the airlock requests. Please see the browser console for details.</p>
        </MessageBar>
      ); break;
    default:
      requestsList = (
        <div style={{ marginTop: '20px' }}>
          <Spinner label="Loading airlock requests" ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
        </div>
      ); break;
  }

  return (
    <>
      <Stack className="tre-panel">
        <Stack.Item>
          <Stack horizontal horizontalAlign="space-between">
            <h1>Airlock</h1>
            {
              <CommandBarButton
                iconProps={{ iconName: 'add' }}
                text="New request"
                style={{ background: 'none', marginBottom: '10px', color: theme.palette.themePrimary }}
              />
            }
          </Stack>
        </Stack.Item>
        <Stack.Item className="tre-resource-panel">
          { requestsList }
        </Stack.Item>
      </Stack>
    </>
  );

};

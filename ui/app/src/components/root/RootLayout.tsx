import { MessageBar, MessageBarType, Spinner, SpinnerSize, Stack } from '@fluentui/react';
import React, { useContext, useEffect, useRef, useState } from 'react';
import { Route, Routes } from 'react-router-dom';
import { Admin } from '../../App';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { Workspace } from '../../models/workspace';
import { useAuthApiCall, HttpMethod, ResultType } from '../../useAuthApiCall';
import { RootRolesContext } from '../shared/RootRolesContext';
import { RootDashboard } from './RootDashboard';
import { LeftNav } from './LeftNav';
import config from '../../config.json';

interface RootLayoutProps {
  selectWorkspace: (workspace: Workspace) => void
}

export const RootLayout: React.FunctionComponent<RootLayoutProps> = (props: RootLayoutProps) => {
  const [workspaces, setWorkspaces] = useState([] as Array<Workspace>);
  const rootRolesContext = useRef(useContext(RootRolesContext));
  const [loadingState, setLoadingState] = useState('loading');
  const apiCall = useAuthApiCall();

  useEffect(() => {
    const getWorkspaces = async () => {
      try {
        const r = await apiCall(ApiEndpoint.Workspaces, HttpMethod.Get, undefined, undefined, ResultType.JSON, (roles: Array<string>) => {
          config.debug && console.log("Root Roles", roles);
          rootRolesContext.current.roles = roles;
          setLoadingState(roles && roles.length > 0 ? 'ok' : 'denied');
        });

        r && r.workspaces && setWorkspaces(r.workspaces);
      } catch {
        setLoadingState('error');
      }

    };
    getWorkspaces();
  }, [apiCall]);

  switch (loadingState) {

    case 'ok':
      return (
        <Stack horizontal className='tre-body-inner'>
          <Stack.Item className='tre-left-nav'>
            <LeftNav />
          </Stack.Item><Stack.Item className='tre-body-content'>
            <Routes>
              <Route path="/" element={<RootDashboard selectWorkspace={props.selectWorkspace} workspaces={workspaces} />} />
              <Route path="/admin" element={<Admin />} />
            </Routes>
          </Stack.Item>
        </Stack>
      );
    case 'denied':
      return (
        <MessageBar
          messageBarType={MessageBarType.warning}
          isMultiline={true}
        >
          <h3>Access Denied</h3>
          <p>
            You do not have access to this application. If you feel you should have access, please speak to your TRE Administrator. <br />
            If you have recently been given access, you may need to clear you browser local storage and refresh.</p>
        </MessageBar>
      );
    case 'error':
      return (
        <MessageBar
          messageBarType={MessageBarType.error}
          isMultiline={true}
        >
          <h3>Error retrieving workspaces</h3>
          <p>We were unable to fetch the workspace list. Please see browser console for details.</p>
        </MessageBar>
      );
    default:
      return (
        <div style={{ marginTop: '20px' }}>
          <Spinner label="Loading TRE" ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
        </div>
      );
  }
};

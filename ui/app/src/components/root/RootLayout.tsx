import { MessageBar, MessageBarType, Spinner, SpinnerSize, Stack } from '@fluentui/react';
import React, { useContext, useEffect, useRef, useState } from 'react';
import { Route, Routes } from 'react-router-dom';
import { Admin } from '../../App';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { Workspace } from '../../models/workspace';
import { useAuthApiCall, HttpMethod, ResultType } from '../../useAuthApiCall';
import { AppRolesContext } from '../../contexts/AppRolesContext';
import { RootDashboard } from './RootDashboard';
import { LeftNav } from './LeftNav';
import config from '../../config.json';
import { LoadingState } from '../../models/loadingState';

export const RootLayout: React.FunctionComponent = () => {
  const [workspaces, setWorkspaces] = useState([] as Array<Workspace>);
  const appRolesContext = useRef(useContext(AppRolesContext));
  const [loadingState, setLoadingState] = useState(LoadingState.Loading);
  const apiCall = useAuthApiCall();

  useEffect(() => {
    const getWorkspaces = async () => {
      try {
        const r = await apiCall(ApiEndpoint.Workspaces, HttpMethod.Get, undefined, undefined, ResultType.JSON, (roles: Array<string>) => {
          config.debug && console.log("Root Roles", roles);
          appRolesContext.current.setAppRoles(roles);
          setLoadingState(roles && roles.length > 0 ? LoadingState.Ok : LoadingState.AccessDenied);
        });

        r && r.workspaces && setWorkspaces(r.workspaces);
      } catch {
        setLoadingState(LoadingState.Error);
      }

    };
    getWorkspaces();
  }, [apiCall]);

  const updateWorkspace = (w: Workspace) => {
    let i = workspaces.findIndex((f: Workspace) => f.id === w.id);
    let ws = [...workspaces]
    ws.splice(i, 1, w);
    setWorkspaces(ws);
  }

  const removeWorkspace = (w: Workspace) => {
    let i = workspaces.findIndex((f: Workspace) => f.id === w.id);
    let ws = [...workspaces];
    ws.splice(i, 1);
    setWorkspaces(ws);
  }

  switch (loadingState) {

    case LoadingState.Ok:
      return (
        <Stack horizontal className='tre-body-inner'>
          <Stack.Item className='tre-left-nav'>
            <LeftNav />
          </Stack.Item><Stack.Item className='tre-body-content'>
            <Routes>
              <Route path="/" element={
                <RootDashboard 
                  workspaces={workspaces} 
                  updateWorkspace={(w: Workspace) => updateWorkspace(w)} 
                  removeWorkspace={(w: Workspace) => removeWorkspace(w)} />
                } />
              <Route path="/admin" element={<Admin />} />
            </Routes>
          </Stack.Item>
        </Stack>
      );
    case LoadingState.AccessDenied:
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
    case LoadingState.Error:
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

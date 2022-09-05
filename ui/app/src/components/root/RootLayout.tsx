import { MessageBar, MessageBarType, Spinner, SpinnerSize, Stack } from '@fluentui/react';
import React, { useEffect, useState } from 'react';
import { Route, Routes } from 'react-router-dom';
import { Admin } from '../../App';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { Workspace } from '../../models/workspace';
import { useAuthApiCall, HttpMethod, ResultType } from '../../hooks/useAuthApiCall';
import { RootDashboard } from './RootDashboard';
import { LeftNav } from './LeftNav';
import { LoadingState } from '../../models/loadingState';
import { SharedServices } from '../shared/SharedServices';
import { SharedServiceItem } from '../shared/SharedServiceItem';
import { SecuredByRole } from '../shared/SecuredByRole';
import { RoleName } from '../../models/roleNames';
import { APIError } from '../../models/exceptions';
import { ExceptionLayout } from '../shared/ExceptionLayout';

export const RootLayout: React.FunctionComponent = () => {
  const [workspaces, setWorkspaces] = useState([] as Array<Workspace>);
  const [loadingState, setLoadingState] = useState(LoadingState.Loading);
  const [apiError, setApiError] = useState({} as APIError);
  const apiCall = useAuthApiCall();

  useEffect(() => {
    const getWorkspaces = async () => {
      try {
        const r = await apiCall(ApiEndpoint.Workspaces, HttpMethod.Get, undefined, undefined, ResultType.JSON);
        setLoadingState(LoadingState.Ok);
        r && r.workspaces && setWorkspaces(r.workspaces);
      } catch (e:any) {
        e.userMessage = 'Error retrieving workspaces';
        setApiError(e);
        setLoadingState(LoadingState.Error);
      }

    };
    getWorkspaces();
  }, [apiCall]);

  const addWorkspace = (w: Workspace) => {
    let ws = [...workspaces]
    ws.push(w);
    setWorkspaces(ws);
  }

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
          <Stack.Item className='tre-left-nav' style={{marginTop:2}}>
            <LeftNav />
          </Stack.Item><Stack.Item className='tre-body-content'>
            <Routes>
              <Route path="/" element={
                <RootDashboard
                  workspaces={workspaces}
                  addWorkspace={(w: Workspace) => addWorkspace(w)}
                  updateWorkspace={(w: Workspace) => updateWorkspace(w)}
                  removeWorkspace={(w: Workspace) => removeWorkspace(w)} />
              } />
              <Route path="/admin" element={<Admin />} />
              <Route path="/shared-services/*" element={
                <Routes>
                  <Route path="/" element={<SecuredByRole element={<SharedServices />} allowedRoles={[RoleName.TREAdmin]} errorString={"You must be a TRE Admin to access this area"}/>} />
                  <Route path=":sharedServiceId" element={<SecuredByRole element={<SharedServiceItem />} allowedRoles={[RoleName.TREAdmin]} errorString={"You must be a TRE Admin to access this area"}/>} />
                </Routes>
              } />
            </Routes>
          </Stack.Item>
        </Stack>
      );
    case LoadingState.Error:
      return (
        <ExceptionLayout e={apiError} />
      );
    default:
      return (
        <div style={{ marginTop: '20px' }}>
          <Spinner label="Loading TRE" ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
        </div>
      );
  }
};

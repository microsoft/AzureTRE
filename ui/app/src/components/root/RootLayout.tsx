import { Spinner, SpinnerSize, Stack } from '@fluentui/react';
import React, { useContext, useEffect, useRef, useState } from 'react';
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
import { AppRolesContext } from '../../contexts/AppRolesContext';
import { CostsContext } from '../../contexts/CostsContext';
import config from "../../config.json";

export const RootLayout: React.FunctionComponent = () => {
  const [workspaces, setWorkspaces] = useState([] as Array<Workspace>);
  const [loadingState, setLoadingState] = useState(LoadingState.Loading);
  const [loadingCostState, setLoadingCostState] = useState(LoadingState.Loading);
  const [apiError, setApiError] = useState({} as APIError);
  const [costApiError, setCostApiError] = useState({} as APIError);
  const apiCall = useAuthApiCall();
  const appRolesCtx = useContext(AppRolesContext);
  const costsWriteCtx = useRef(useContext(CostsContext));

  useEffect(() => {
    const getWorkspaces = async () => {
      try {
        const r = await apiCall(ApiEndpoint.Workspaces, HttpMethod.Get, undefined, undefined, ResultType.JSON);
        setLoadingState(LoadingState.Ok);
        r && r.workspaces && setWorkspaces(r.workspaces);
      } catch (e:any) {
        e.userMessage = 'Error retrieving resources';
        setApiError(e);
        setLoadingState(LoadingState.Error);
      }
    };

    getWorkspaces();
  }, [apiCall]);


  useEffect(() => {
    const getCosts = async () => {
      try {
        const r = await apiCall(ApiEndpoint.Costs, HttpMethod.Get, undefined, undefined, ResultType.JSON);

        costsWriteCtx.current.setCosts([
          ...r.workspaces,
          ...r.shared_services
        ]);

        setLoadingCostState(LoadingState.Ok);
      }
      catch (e:any) {
        if (e instanceof APIError && e.status === 404) {
          config.debug && console.warn(e.message);
          setLoadingCostState(LoadingState.NotSupported);
        }
        else {
          e.userMessage = 'Error retrieving costs';
          setLoadingCostState(LoadingState.Error);
        }

        setCostApiError(e);
      }
    };

    if (appRolesCtx.roles.includes(RoleName.TREAdmin)) {
      getCosts();
    }

    const ctx = costsWriteCtx.current;

    // run this on unmount - to clear the context
    return (() => ctx.setCosts([]));
  }, [apiCall, appRolesCtx.roles]);

  const addWorkspace = (w: Workspace) => {
    const ws = [...workspaces]
    ws.push(w);
    setWorkspaces(ws);
  }

  const updateWorkspace = (w: Workspace) => {
    const i = workspaces.findIndex((f: Workspace) => f.id === w.id);
    const ws = [...workspaces]
    ws.splice(i, 1, w);
    setWorkspaces(ws);
  }

  const removeWorkspace = (w: Workspace) => {
    const i = workspaces.findIndex((f: Workspace) => f.id === w.id);
    const ws = [...workspaces];
    ws.splice(i, 1);
    setWorkspaces(ws);
  }

  switch (loadingState) {
    case LoadingState.Ok:
      return (
        <>
        {
        loadingCostState === LoadingState.Error &&
        <ExceptionLayout e={costApiError} />
        }
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
        </>
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

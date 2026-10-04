import { Spinner, SpinnerSize, Stack } from "@fluentui/react";
import React, { useCallback, useContext, useEffect, useRef, useState } from "react";
import { Route, Routes } from "react-router-dom";
import { Admin } from "../../App";
import { ApiEndpoint } from "../../models/apiEndpoints";
import { Workspace } from "../../models/workspace";
import { useAuthApiCall, HttpMethod, ResultType } from "../../hooks/useAuthApiCall";
import { RootDashboard } from "./RootDashboard";
import { LeftNav } from "./LeftNav";
import { LoadingState } from "../../models/loadingState";
import { RequestsList } from "../shared/RequestsList";
import { SharedServices } from "../shared/SharedServices";
import { SharedServiceItem } from "../shared/SharedServiceItem";
import { SecuredByRole } from "../shared/SecuredByRole";
import { RoleName } from "../../models/roleNames";
import { APIError, isRetryableApiError } from "../../models/exceptions";
import { ExceptionLayout } from "../shared/ExceptionLayout";
import { AppRolesContext } from "../../contexts/AppRolesContext";
import { CostsContext } from "../../contexts/CostsContext";
import config from "../../config.json";
import { useRefresh } from "../../hooks/useRefresh";

export const RootLayout: React.FunctionComponent = () => {
  const [workspaces, setWorkspaces] = useState([] as Array<Workspace>);
  const [loadingState, setLoadingState] = useState(LoadingState.Loading);
  const [loadingCostState, setLoadingCostState] = useState(LoadingState.Loading);
  const [apiError, setApiError] = useState({} as APIError);
  const apiCall = useAuthApiCall();
  const appRolesCtx = useContext(AppRolesContext);
  const costsWriteCtx = useRef(useContext(CostsContext));
  const hasLoadedWorkspaces = useRef(false);

  const getWorkspaces = useCallback(async () => {
    try {
      const r = await apiCall(ApiEndpoint.Workspaces, HttpMethod.Get, undefined, undefined, ResultType.JSON);
      hasLoadedWorkspaces.current = true;
      setLoadingState(LoadingState.Ok);
      r && r.workspaces && setWorkspaces(r.workspaces);
    } catch (e: any) {
      e.userMessage = "Error retrieving resources";
      setApiError(e);
      // Keep the loaded list only for transient failures; terminal errors replace it with the error view.
      if (!hasLoadedWorkspaces.current || !isRetryableApiError(e)) {
        setLoadingState(LoadingState.Error);
      }
    }
  }, [apiCall]);
  const refreshWorkspaces = useRefresh(getWorkspaces);

  // Load through the refresh hook so the initial request is serialized with manual and polling refreshes.
  useEffect(() => {
    refreshWorkspaces();
  }, [getWorkspaces, refreshWorkspaces]);

  useEffect(() => {
    let active = true;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    const markNotSupported = () => {
      costsWriteCtx.current.setCosts([]);
      setLoadingCostState(LoadingState.NotSupported);
      costsWriteCtx.current.setLoadingState(LoadingState.NotSupported);
    };
    const getCosts = async () => {
      if (!active) return;
      try {
        if (appRolesCtx.roles.includes(RoleName.TREAdmin)) {
          costsWriteCtx.current.setLoadingState(LoadingState.Loading);
          const r = await apiCall(ApiEndpoint.Costs, HttpMethod.Get, undefined, undefined, ResultType.JSON);
          if (!active) return;
          costsWriteCtx.current.setCosts([...r.workspaces, ...r.shared_services]);

          costsWriteCtx.current.setLoadingState(LoadingState.Ok);
          setLoadingCostState(LoadingState.Ok);
        } else {
          costsWriteCtx.current.setLoadingState(LoadingState.AccessDenied);
          setLoadingCostState(LoadingState.AccessDenied);
        }
      } catch (e: any) {
        if (!active) return;
        if (e instanceof APIError && (e.status === 429 || e.status === 503)) {
          let retryAfter = 0;
          try {
            retryAfter = Number(e.message && JSON.parse(e.message).error?.["retry-after"]);
          } catch {
            retryAfter = 0;
          }
          if (retryAfter > 0) {
            // Stay in the loading state while the server-requested retry is pending.
            config.debug && console.info("retrying cost request after " + retryAfter + " seconds");
            retryTimer = setTimeout(getCosts, retryAfter * 1000);
            return;
          }
        } else if (e instanceof APIError && e.status === 404 /*subscription not supported*/) {
          config.debug && console.warn(e.message);
        }
        markNotSupported();
      }
    };

    getCosts();

    const ctx = costsWriteCtx.current;

    // run this on unmount - to clear the context
    return () => {
      active = false;
      if (retryTimer) clearTimeout(retryTimer);
      ctx.setCosts([]);
    };
  }, [apiCall, appRolesCtx.roles]);

  const addWorkspace = (w: Workspace) => {
    const ws = [...workspaces];
    ws.push(w);
    setWorkspaces(ws);
  };

  const updateWorkspace = (w: Workspace) => {
    const i = workspaces.findIndex((f: Workspace) => f.id === w.id);
    const ws = [...workspaces];
    ws.splice(i, 1, w);
    setWorkspaces(ws);
  };

  const removeWorkspace = (w: Workspace) => {
    const i = workspaces.findIndex((f: Workspace) => f.id === w.id);
    const ws = [...workspaces];
    ws.splice(i, 1);
    setWorkspaces(ws);
  };

  switch (loadingState) {
    case LoadingState.Ok:
      return (
        <>
          <Stack horizontal className="tre-body-inner">
            <Stack.Item className="tre-left-nav" style={{ marginTop: 2 }}>
              <LeftNav />
            </Stack.Item>
            <Stack.Item id="tre-body" className="tre-body-content">
              <Routes>
                <Route
                  path="/"
                  element={
                    <RootDashboard
                      workspaces={workspaces}
                      addWorkspace={(w: Workspace) => addWorkspace(w)}
                      updateWorkspace={(w: Workspace) => updateWorkspace(w)}
                      removeWorkspace={(w: Workspace) => removeWorkspace(w)}
                      onRefresh={refreshWorkspaces}
                    />
                  }
                />
                <Route path="/admin" element={<Admin />} />
                <Route
                  path="/shared-services/*"
                  element={
                    <Routes>
                      <Route
                        path="/"
                        element={
                          <SecuredByRole
                            element={<SharedServices />}
                            allowedAppRoles={[RoleName.TREAdmin]}
                            errorString={"You must be a TRE Admin to access this area"}
                          />
                        }
                      />
                      <Route
                        path=":sharedServiceId"
                        element={
                          <SecuredByRole
                            element={<SharedServiceItem />}
                            allowedAppRoles={[RoleName.TREAdmin]}
                            errorString={"You must be a TRE Admin to access this area"}
                          />
                        }
                      />
                    </Routes>
                  }
                />
                <Route
                  path="/requests/*"
                  element={
                    <Routes>
                      <Route path="/" />
                      <Route path="airlock/*" element={<RequestsList />} />
                    </Routes>
                  }
                />
              </Routes>
            </Stack.Item>
          </Stack>
        </>
      );
    case LoadingState.Error:
      return <ExceptionLayout e={apiError} onRetry={refreshWorkspaces} />;
    default:
      return (
        <div style={{ marginTop: "20px" }}>
          <Spinner label="Loading TRE" ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
        </div>
      );
  }
};

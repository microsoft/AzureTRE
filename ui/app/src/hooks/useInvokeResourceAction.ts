import { useCallback, useContext } from "react";
import { WorkspaceContext } from "../contexts/WorkspaceContext";
import { ApiEndpoint } from "../models/apiEndpoints";
import { Resource } from "../models/resource";
import { addUpdateOperation } from "../components/shared/notifications/operationsSlice";
import { useAppDispatch } from "./customReduxHooks";
import { HttpMethod, useAuthApiCall } from "./useAuthApiCall";

// Invokes a template custom action (for example start/stop) and tracks the resulting operation.
export const useInvokeResourceAction = () => {
  const apiCall = useAuthApiCall();
  const workspaceCtx = useContext(WorkspaceContext);
  const dispatch = useAppDispatch();
  const workspaceScopeId = workspaceCtx.workspaceApplicationIdURI;

  return useCallback(
    async (resource: Resource, actionName: string) => {
      const action = await apiCall(
        `${resource.resourcePath}/${ApiEndpoint.InvokeAction}?action=${actionName}`,
        HttpMethod.Post,
        workspaceScopeId,
      );
      action && action.operation && dispatch(addUpdateOperation(action.operation));
    },
    [apiCall, dispatch, workspaceScopeId],
  );
};

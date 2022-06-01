import { useContext, useEffect, useRef, useState } from "react";
import { NotificationsContext } from "../contexts/NotificationsContext";
import { WorkspaceContext } from "../contexts/WorkspaceContext";
import { ResourceUpdate, ComponentAction, getResourceFromResult, Resource } from "../models/resource";
import { HttpMethod, useAuthApiCall } from "./useAuthApiCall";

export const useComponentManager = (resource: Resource, onUpdate: (r: Resource) => void) => {
  const opsReadContext = useContext(NotificationsContext);
  const opsWriteContext = useRef(useContext(NotificationsContext));
  const [componentAction, setComponentAction] = useState(ComponentAction.None);
  const workspaceCtx = useContext(WorkspaceContext);
  const apiCall = useAuthApiCall();

  // set the latest component action
  useEffect(() => {
    let updates = opsReadContext.resourceUpdates.filter((r: ResourceUpdate) => { return r.resourceId === resource.id });
    setComponentAction((updates && updates.length > 0) ?
      updates[updates.length - 1].componentAction :
      ComponentAction.None);
  }, [opsReadContext.resourceUpdates, resource.id])

  // act on component action changes
  useEffect(() => {
    const checkForReload = async () => {
      if (componentAction === ComponentAction.Reload) {
        let result = await apiCall(resource.resourcePath, HttpMethod.Get, workspaceCtx.workspaceClientId);
        onUpdate(getResourceFromResult(result));
        opsWriteContext.current.clearUpdatesForResource(resource.id);
      } else if (componentAction === ComponentAction.Remove) {
        opsWriteContext.current.clearUpdatesForResource(resource.id);
      }
    }
    checkForReload();
  }, [apiCall, componentAction, workspaceCtx.workspaceClientId, resource.id, onUpdate, resource.resourcePath]);

  return componentAction;
}

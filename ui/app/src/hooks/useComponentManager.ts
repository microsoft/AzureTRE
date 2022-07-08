import { useContext, useEffect, useRef, useState } from "react";
import { NotificationsContext } from "../contexts/NotificationsContext";
import { WorkspaceContext } from "../contexts/WorkspaceContext";
import { ResourceUpdate, ComponentAction, getResourceFromResult, Resource } from "../models/resource";
import { HttpMethod, useAuthApiCall } from "./useAuthApiCall";

export const useComponentManager = (resource: Resource, onUpdate: (r: Resource) => void, onRemove: (r: Resource) => void) => {
  const opsReadContext = useContext(NotificationsContext);
  const opsWriteContext = useRef(useContext(NotificationsContext));
  const [latestUpdate, setLatestUpdate] = useState({} as ResourceUpdate);
  const workspaceCtx = useContext(WorkspaceContext);
  const apiCall = useAuthApiCall();

  // set the latest component action
  useEffect(() => {
    let updates = opsReadContext.resourceUpdates.filter((r: ResourceUpdate) => { return r.resourceId === resource.id });
    setLatestUpdate((updates && updates.length > 0) ?
      updates[updates.length - 1] :
      { componentAction: ComponentAction.None } as ResourceUpdate);
  }, [opsReadContext.resourceUpdates, resource.id])

  // act on component action changes
  useEffect(() => {
    const checkForReload = async () => {
      if (latestUpdate.componentAction === ComponentAction.Reload) {
        let result = await apiCall(resource.resourcePath, HttpMethod.Get, workspaceCtx.workspaceApplicationIdURI);
        opsWriteContext.current.clearUpdatesForResource(resource.id);
        onUpdate(getResourceFromResult(result));
      } else if (latestUpdate.componentAction === ComponentAction.Remove) {
        opsWriteContext.current.clearUpdatesForResource(resource.id);
        onRemove(resource);
      }
    }
    checkForReload();
  }, [apiCall, latestUpdate, workspaceCtx.workspaceApplicationIdURI, resource, onUpdate, onRemove, resource.resourcePath]);

  return latestUpdate;
}

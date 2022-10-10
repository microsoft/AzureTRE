import { useContext, useEffect, useState } from "react";
import { WorkspaceContext } from "../contexts/WorkspaceContext";
import { completedStates, inProgressStates, Operation } from "../models/operation";
import { ResourceUpdate, ComponentAction, getResourceFromResult, Resource } from "../models/resource";
import { ResourceType } from "../models/resourceType";
import { HttpMethod, useAuthApiCall } from "./useAuthApiCall";
import { useAppSelector } from './customReduxHooks';

export const useComponentManager = (resource: Resource, onUpdate: (r: Resource) => void, onRemove: (r: Resource) => void) => {
  const [latestUpdate, setLatestUpdate] = useState({ componentAction: ComponentAction.None, operation: {} as Operation } as ResourceUpdate);
  const workspaceCtx = useContext(WorkspaceContext);
  const apiCall = useAuthApiCall();
  const operations = useAppSelector((state) => state.operations);

  useEffect(() => {
    const checkOps = async () => {
      let resourceOps = operations.items.filter((o: Operation) => o.resourceId === resource.id);
      if (resourceOps && resourceOps.length > 0){
        let latestOp = resourceOps[resourceOps.length - 1];

        // only act when a status has changed
        if (latestOp.status === latestUpdate.operation.status) return;

        if (inProgressStates.includes(latestOp.status)) {
          setLatestUpdate({componentAction:ComponentAction.Lock, operation: latestOp});
        } else if (completedStates.includes(latestOp.status)) {
          if (latestOp.status === "deleted"){
            onRemove(resource);
          } else {
            setLatestUpdate({componentAction:ComponentAction.Reload, operation: latestOp});

            // if it's transitioned from an in-progress to a completed state, we need to reload it
            if (inProgressStates.includes(latestUpdate.operation.status)) {
              let result = await apiCall(resource.resourcePath, HttpMethod.Get, resource.resourceType === ResourceType.Workspace ? undefined : workspaceCtx.workspaceApplicationIdURI);
              onUpdate(getResourceFromResult(result));
            }
          }
        } else {
          setLatestUpdate({componentAction:ComponentAction.None, operation: latestOp});
        }
      }
    }

    checkOps();
  }, [operations.items, apiCall, latestUpdate.operation.status, onRemove, onUpdate, resource, workspaceCtx.workspaceApplicationIdURI]);

  return latestUpdate;
}

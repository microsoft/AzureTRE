import React from "react";
import { Operation } from "../models/operation";
import { ResourceUpdate } from "../models/resource";

export const NotificationsContext = React.createContext({
  operations: [] as Array<Operation>,
  addOperations: (ops: Array<Operation>) => {},
  resourceUpdates: [] as Array<ResourceUpdate>,
  addResourceUpdate: (r: ResourceUpdate) => {},
  clearUpdatesForResource: (resourceId: string) => {}
});

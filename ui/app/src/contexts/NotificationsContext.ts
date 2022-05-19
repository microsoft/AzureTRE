import React from "react";
import { Operation } from "../models/operation";
import { ResourceUpdate } from "../models/resource";

export const NotificationsContext = React.createContext({
  latestOperation: {} as Operation,
  addOperation: (op: Operation) => {},
  resourceUpdates: [] as Array<ResourceUpdate>,
  addResourceUpdate: (r: ResourceUpdate) => {},
  clearUpdatesForResource: (resourceId: string) => {}
});

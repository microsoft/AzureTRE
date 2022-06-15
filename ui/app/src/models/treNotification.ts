import { Operation } from "./operation";
import { Resource } from "./resource";
import { Workspace } from "./workspace";

export interface TRENotification {
    operation: Operation, 
    resource: Resource,
    workspace?: Workspace
  }
  
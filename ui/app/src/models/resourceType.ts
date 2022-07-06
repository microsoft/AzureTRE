import { Resource } from "./resource";
import { Workspace } from "./workspace";
import { WorkspaceService } from "./workspaceService";

export enum ResourceType {
    Workspace = "workspace",
    WorkspaceService = "workspace-service",
    UserResource = "user-resource",
    SharedService = "shared-service"
}

export interface CreateFormResource {
  resourceType: ResourceType,
  resourceParent?: Workspace | WorkspaceService,
  updateResource?: Resource,
  onAdd?: (r: Resource) => void,
  workspaceApplicationIdURI?: string
}

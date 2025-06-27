import { Resource } from "./resource";

export interface UserResource extends Resource {
  parentWorkspaceServiceId: string;
  ownerId: string;
}

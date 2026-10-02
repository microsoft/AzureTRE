import { Resource } from "./resource";

export interface UserResource extends Resource {
  parentWorkspaceServiceId: string;
  ownerId: string;
}

export const isOwnedByUser = (resource: UserResource, userId: string): boolean =>
  !!userId &&
  (resource.ownerId === userId || resource.properties?.owner_id === userId || resource.properties?.ownerId === userId);

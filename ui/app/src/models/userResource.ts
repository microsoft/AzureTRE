import { Resource } from "./resource";

export interface UserResource extends Resource {
  parentWorkspaceServiceId: string;
  ownerId: string;
}

// ownerId is authoritative; template properties are only a legacy fallback when it is absent.
export const isOwnedByUser = (resource: UserResource, userId: string): boolean =>
  !!userId && (resource.ownerId || resource.properties?.owner_id || resource.properties?.ownerId) === userId;

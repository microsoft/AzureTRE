import { Resource } from "./resource";

export interface UserResource extends Resource {
    workspaceServiceId: string
}
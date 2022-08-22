import { Resource } from "./resource";

export interface AirlockRequest extends Resource {
  workspaceId: string;
  requestType: AirlockRequestType;
  files: Array<string>;
  businessJustification: string;
  errorMessage: null | string;
  status: AirlockRequestStatus;
}

export enum AirlockRequestType {
  Import = 'import',
  Export = 'export'
}

export enum AirlockRequestStatus {
  Draft = 'draft',
  InReview = 'in-review',
  InProgress = 'in-progress',
  Approved = 'approved',
  Rejected = 'rejected'
}

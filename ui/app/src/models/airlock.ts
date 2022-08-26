import { Resource } from "./resource";

export interface AirlockRequest extends Resource {
  workspaceId: string;
  requestType: AirlockRequestType;
  files: Array<string>;
  businessJustification: string;
  errorMessage: null | string;
  status: AirlockRequestStatus;
  creationTime: number;
}

export enum AirlockRequestType {
  Import = 'import',
  Export = 'export'
}

export enum AirlockRequestStatus {
  Draft = 'draft',
  InReview = 'in_review',
  InProgress = 'in_progress',
  Approved = 'approved',
  Rejected = 'rejected',
  Submitted = 'submitted',
  Cancelled = 'cancelled'
}

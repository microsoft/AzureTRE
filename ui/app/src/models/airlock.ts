import { Resource } from "./resource";
import { User } from "./user";

export interface AirlockRequest extends Resource {
  workspaceId: string;
  requestType: AirlockRequestType;
  files: Array<string>;
  businessJustification: string;
  errorMessage: null | string;
  status: AirlockRequestStatus;
  creationTime: number;
  allowed_user_actions: Array<AirlockRequestAction>;
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
  ApprovalInProgress = 'approval_in_progress',
  RejectionInProgress = 'rejection_in_progress',
  Rejected = 'rejected',
  Blocked = 'blocked',
  Submitted = 'submitted',
  Cancelled = 'cancelled',
  Failed = 'failed'
}

export interface NewAirlockRequest {
  requestType: AirlockRequestType;
  businessJustification: string;
}

export enum AirlockRequestAction {
  Cancel = 'cancel',
  Submit = 'submit',
  Review = 'review'
}

export const AirlockFilesLinkInvalidStatus = [
  AirlockRequestStatus.Rejected,
  AirlockRequestStatus.Blocked,
  AirlockRequestStatus.Failed
]

export interface AirlockReview {
  reviewId: string,
  dateCreated: number,
  reviewDecision: string,
  decisionExplanation: string,
  reviewer: User
}

import { User } from "./user";

export interface AirlockRequest {
  id: string;
  resourceVersion: number;
  createdBy: User;
  createdWhen: number;
  updatedBy: User;
  updatedWhen: number;
  history: Array<AirlockRequestHistoryItem>;
  workspaceId: string;
  type: AirlockRequestType;
  files: Array<{ name: string; size: number }>;
  title: string;
  businessJustification: string;
  status: AirlockRequestStatus;
  reviewUserResources: { [key: string]: AirlockReviewUserResource };
  allowedUserActions: Array<AirlockRequestAction>;
  reviews?: Array<AirlockReview>;
  statusMessage?: string;
  etag?: string;
}

export interface AirlockRequestHistoryItem {
  resourceVersion: number;
  updatedWhen: number;
  updatedBy: User;
  properties: {};
}

export enum AirlockRequestType {
  Import = "import",
  Export = "export",
}

export enum AirlockRequestStatus {
  Draft = "draft",
  InReview = "in_review",
  Approved = "approved",
  ApprovalInProgress = "approval_in_progress",
  RejectionInProgress = "rejection_in_progress",
  Rejected = "rejected",
  Blocked = "blocked",
  BlockingInProgress = "blocking_in_progress",
  Submitted = "submitted",
  Cancelled = "cancelled",
  Failed = "failed",
  Revoked = "revoked",
}

export interface NewAirlockRequest {
  type: AirlockRequestType;
  title: string;
  businessJustification: string;
}

export enum AirlockRequestAction {
  Cancel = "cancel",
  Submit = "submit",
  Review = "review",
  Revoke = "revoke",
}

export const AirlockFilesLinkValidStatus = [
  AirlockRequestStatus.Draft,
  AirlockRequestStatus.Approved,
];

export enum AirlockReviewDecision {
  Approved = "approved",
  Rejected = "rejected",
  Revoked = "revoked",
}

export interface AirlockReview {
  id: string;
  dateCreated: number;
  reviewDecision: AirlockReviewDecision;
  decisionExplanation: string;
  reviewer: User;
}

export interface AirlockReviewUserResource {
  workspaceId: string;
  workspaceServiceId: string;
  userResourceId: string;
}

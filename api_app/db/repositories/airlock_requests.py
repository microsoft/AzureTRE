import copy
import uuid

from datetime import datetime, timezone, UTC
from typing import List, Optional, Union
from pydantic import UUID4
from azure.cosmos.exceptions import CosmosResourceNotFoundError, CosmosAccessConditionFailedError
from fastapi import HTTPException, status
from pydantic import TypeAdapter
from db.repositories.workspaces import WorkspaceRepository
from services.authentication import get_aad_service
from models.domain.authentication import User
from db.errors import EntityDoesNotExist
from models.domain.airlock_request import AirlockFile, AirlockRequest, AirlockRequestStatus, \
    AirlockReview, AirlockReviewDecision, AirlockRequestHistoryItem, AirlockRequestType, AirlockReviewUserResource
from models.schemas.airlock_request import AirlockRequestInCreate, AirlockReviewInCreate
from core import config
from resources import strings
from db.repositories.base import BaseRepository
from services.logging import logger

# Sentinel so callers can distinguish "leave unchanged" from "clear" (None) for optional fields.
_UNSET = object()


class AirlockRequestRepository(BaseRepository):
    FINAL_AIRLOCK_STATUSES = [
        AirlockRequestStatus.Approved,
        AirlockRequestStatus.Rejected,
        AirlockRequestStatus.Blocked,
        AirlockRequestStatus.Cancelled,
        AirlockRequestStatus.Failed,
        AirlockRequestStatus.Revoked
    ]

    @classmethod
    async def create(cls):
        cls = AirlockRequestRepository()
        await super().create(config.STATE_STORE_AIRLOCK_REQUESTS_CONTAINER)
        return cls

    @staticmethod
    def get_resource_base_spec_params():
        return {"tre_id": config.TRE_ID}

    def get_timestamp(self) -> float:
        return datetime.now(timezone.utc).timestamp()

    async def update_airlock_request_item(self, original_request: AirlockRequest, new_request: AirlockRequest, updated_by: Union[User, dict], request_properties: dict) -> AirlockRequest:
        history_item = AirlockRequestHistoryItem(
            resourceVersion=original_request.resourceVersion,
            updatedWhen=original_request.updatedWhen,
            updatedBy=original_request.updatedBy,
            properties=request_properties
        )
        new_request.history.append(history_item)

        # now update the request props
        new_request.resourceVersion = new_request.resourceVersion + 1
        if hasattr(updated_by, "model_dump"):
            new_request.updatedBy = updated_by.model_dump()
        elif isinstance(updated_by, dict):
            new_request.updatedBy = updated_by
        else:
            raise TypeError("updated_by must be a User model or dict")
        new_request.updatedWhen = self.get_timestamp()

        await self.upsert_item_with_etag(new_request, new_request.etag)
        return new_request

    @staticmethod
    def airlock_requests_query():
        return 'SELECT * FROM c'

    async def set_default_airlock_version_for_legacy_requests(self) -> List[str]:
        # Requests created before airlock v2 predate the airlock_version field and hold their data in
        # legacy storage. The model now defaults missing values to v2, so stamp existing requests with v1.
        query = 'SELECT * FROM c WHERE NOT IS_DEFINED(c.airlock_version)'
        migrated = []
        for request in await self.query(query=query):
            request['airlock_version'] = 1
            await self.update_item_dict(request)
            migrated.append(request['id'])
        return migrated

    async def get_in_flight_airlock_request_ids_for_workspace(self, workspace_id: str) -> List[str]:
        query = (
            "SELECT c.id FROM c WHERE c.workspaceId = @workspaceId "
            "AND NOT ARRAY_CONTAINS(@finalStatuses, c.status)"
        )
        parameters = [
            {"name": "@workspaceId", "value": str(workspace_id)},
            {"name": "@finalStatuses", "value": [status.value for status in self.FINAL_AIRLOCK_STATUSES]}
        ]
        requests = await self.query(query=query, parameters=parameters)
        return [request["id"] for request in requests]

    async def get_data_retaining_airlock_request_ids_for_workspace(self, workspace_id: str) -> List[str]:
        # Any request that isn't Cancelled may still have data in the workspace's per-stage (v1)
        # storage (approved imports especially); cancelled requests have their containers deleted.
        query = "SELECT c.id FROM c WHERE c.workspaceId = @workspaceId AND c.status != @cancelled"
        parameters = [
            {"name": "@workspaceId", "value": str(workspace_id)},
            {"name": "@cancelled", "value": AirlockRequestStatus.Cancelled.value}
        ]
        requests = await self.query(query=query, parameters=parameters)
        return [request["id"] for request in requests]

    def validate_status_update(self, current_status: AirlockRequestStatus, new_status: AirlockRequestStatus) -> bool:

        # Define valid transitions
        valid_transitions = {
            AirlockRequestStatus.Draft: {
                AirlockRequestStatus.Submitted,
                AirlockRequestStatus.Cancelled,
                AirlockRequestStatus.Failed
            },
            AirlockRequestStatus.Submitted: {
                AirlockRequestStatus.InReview,
                AirlockRequestStatus.BlockingInProgress,
                AirlockRequestStatus.Failed
            },
            AirlockRequestStatus.InReview: {
                AirlockRequestStatus.ApprovalInProgress,
                AirlockRequestStatus.RejectionInProgress,
                AirlockRequestStatus.Cancelled,
                AirlockRequestStatus.Failed
            },
            AirlockRequestStatus.ApprovalInProgress: {
                AirlockRequestStatus.Approved,
                AirlockRequestStatus.Failed
            },
            AirlockRequestStatus.RejectionInProgress: {
                AirlockRequestStatus.Rejected,
                AirlockRequestStatus.Failed
            },
            AirlockRequestStatus.BlockingInProgress: {
                AirlockRequestStatus.Blocked,
                AirlockRequestStatus.Failed
            },
            AirlockRequestStatus.Approved: {
                AirlockRequestStatus.Revoked
            },
            # Final states - no transitions allowed
            AirlockRequestStatus.Rejected: set(),
            AirlockRequestStatus.Blocked: set(),
            AirlockRequestStatus.Cancelled: set(),
            AirlockRequestStatus.Failed: set(),
            AirlockRequestStatus.Revoked: set()
        }

        # Check if the transition is valid
        allowed_transitions = valid_transitions.get(current_status, set())
        return new_status in allowed_transitions

    def create_airlock_request_item(self, airlock_request_input: AirlockRequestInCreate, workspace_id: str, user, airlock_version: int = 2) -> AirlockRequest:
        full_airlock_request_id = str(uuid.uuid4())

        resource_spec_parameters = {**self.get_airlock_request_spec_params()}

        airlock_request = AirlockRequest(
            id=full_airlock_request_id,
            workspaceId=workspace_id,
            title=airlock_request_input.title,
            businessJustification=airlock_request_input.businessJustification,
            type=airlock_request_input.type,
            createdBy=user,
            createdWhen=datetime.now(UTC).timestamp(),
            updatedBy=user,
            updatedWhen=datetime.now(UTC).timestamp(),
            properties=resource_spec_parameters,
            reviews=[],
            airlock_version=airlock_version
        )

        return airlock_request

    async def get_airlock_requests(self, workspace_id: Optional[str] = None, creator_user_id: Optional[str] = None, type: Optional[AirlockRequestType] = None, status: Optional[AirlockRequestStatus] = None, order_by: Optional[str] = None, order_ascending=True) -> List[AirlockRequest]:
        query = self.airlock_requests_query()

        # optional filters
        conditions = []
        parameters = []
        if workspace_id:
            conditions.append('c.workspaceId=@workspace_id')
            parameters.append({"name": "@workspace_id", "value": workspace_id})
        if creator_user_id:
            conditions.append('c.createdBy.id=@user_id')
            parameters.append({"name": "@user_id", "value": creator_user_id})
        if status:
            conditions.append('c.status=@status')
            parameters.append({"name": "@status", "value": status})
        if type:
            conditions.append('c.type=@type')
            parameters.append({"name": "@type", "value": type})

        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

        # optional sorting
        if order_by:
            query += ' ORDER BY c.' + order_by
            query += ' ASC' if order_ascending else ' DESC'

        airlock_requests = await self.query(query=query, parameters=parameters)
        return TypeAdapter(List[AirlockRequest]).validate_python(airlock_requests)

    async def get_airlock_request_by_id(self, airlock_request_id: UUID4) -> AirlockRequest:
        try:
            airlock_requests = await self.read_item_by_id(str(airlock_request_id))
        except CosmosResourceNotFoundError:
            raise EntityDoesNotExist
        return TypeAdapter(AirlockRequest).validate_python(airlock_requests)

    async def get_airlock_requests_for_airlock_manager(self, user_id: str, type: Optional[AirlockRequestType] = None, status: Optional[AirlockRequestStatus] = None, order_by: Optional[str] = None, order_ascending=True) -> List[AirlockRequest]:
        workspace_repo = await WorkspaceRepository.create()
        access_service = get_aad_service()

        workspaces = await workspace_repo.get_active_workspaces()
        user_role_assignments = access_service.get_identity_role_assignments(user_id)

        valid_roles = {ra.role_id for ra in user_role_assignments}

        workspace_ids = [
            workspace.id
            for workspace in workspaces
            if workspace.properties["app_role_id_workspace_airlock_manager"] in valid_roles
        ]
        requests = []

        for workspace_id in workspace_ids:
            requests += await self.get_airlock_requests(workspace_id=workspace_id, type=type, status=status, order_by=order_by, order_ascending=order_ascending)

        return requests

    async def update_airlock_request(
            self,
            original_request: AirlockRequest,
            updated_by: Union[User, dict],
            new_status: Optional[AirlockRequestStatus] = None,
            request_files: Optional[List[AirlockFile]] = None,
            status_message: Optional[str] = None,
            airlock_review: Optional[AirlockReview] = None,
            review_user_resource: Optional[AirlockReviewUserResource] = None,
            pending_scan_result=_UNSET) -> AirlockRequest:
        updated_request = self._build_updated_request(
            original_request=original_request,
            new_status=new_status,
            request_files=request_files,
            status_message=status_message,
            airlock_review=airlock_review,
            review_user_resource=review_user_resource,
            pending_scan_result=pending_scan_result,
            updated_by=updated_by)
        try:
            db_response = await self.update_airlock_request_item(original_request, updated_request, updated_by, {"previousStatus": original_request.status})
        except CosmosAccessConditionFailedError:
            logger.warning(f"ETag mismatch for request ID: '{original_request.id}'. Retrying.")
            original_request = await self.get_airlock_request_by_id(original_request.id)
            updated_request = self._build_updated_request(original_request=original_request, new_status=new_status, request_files=request_files, status_message=status_message, airlock_review=airlock_review)
            db_response = await self.update_airlock_request_item(original_request, updated_request, updated_by, {"previousStatus": original_request.status})

        return db_response

    def get_airlock_request_spec_params(self):
        return self.get_resource_base_spec_params()

    def create_airlock_review_item(self, airlock_review_input: AirlockReviewInCreate, reviewer: User) -> AirlockReview:
        full_airlock_review_id = str(uuid.uuid4())
        airlock_review_decision_from_bool = AirlockReviewDecision.Approved if airlock_review_input.approval else AirlockReviewDecision.Rejected

        airlock_review = AirlockReview(
            id=full_airlock_review_id,
            dateCreated=self.get_timestamp(),
            reviewDecision=airlock_review_decision_from_bool,
            decisionExplanation=airlock_review_input.decisionExplanation,
            reviewer=reviewer
        )

        return airlock_review

    def create_airlock_revoke_review_item(self, revocation_reason: str, reviewer: User) -> AirlockReview:
        full_airlock_review_id = str(uuid.uuid4())

        airlock_review = AirlockReview(
            id=full_airlock_review_id,
            dateCreated=self.get_timestamp(),
            reviewDecision=AirlockReviewDecision.Revoked,
            decisionExplanation=revocation_reason,
            reviewer=reviewer
        )

        return airlock_review

    def _build_updated_request(
            self,
            original_request: AirlockRequest,
            new_status: Optional[AirlockRequestStatus] = None,
            request_files: Optional[List[AirlockFile]] = None,
            status_message: Optional[Optional[str]] = None,
            airlock_review: Optional[AirlockReview] = None,
            review_user_resource: Optional[AirlockReviewUserResource] = None,
            pending_scan_result=_UNSET,
            updated_by: Optional[Union[User, dict]] = None) -> AirlockRequest:
        updated_request = copy.deepcopy(original_request)

        if new_status is not None:
            self._validate_status_update(current_status=original_request.status, new_status=new_status)
            updated_request.status = new_status

        if pending_scan_result is not _UNSET:
            updated_request.pendingScanResult = pending_scan_result

        if status_message is not None:
            updated_request.statusMessage = status_message

        if request_files is not None:
            updated_request.files = request_files

        if airlock_review is not None:
            if updated_request.reviews is None:
                updated_request.reviews = [airlock_review]
            else:
                updated_request.reviews.append(airlock_review)

        if review_user_resource is not None and updated_by is not None:
            reviewer_id = updated_by.id if hasattr(updated_by, "id") else updated_by.get("id")
            if reviewer_id:
                updated_request.reviewUserResources[reviewer_id] = review_user_resource

        return updated_request

    def _validate_status_update(self, current_status, new_status):
        if not self.validate_status_update(current_status=current_status, new_status=new_status):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.AIRLOCK_REQUEST_ILLEGAL_STATUS_CHANGE)

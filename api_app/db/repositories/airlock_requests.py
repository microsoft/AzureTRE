import copy
import uuid

from datetime import datetime, timezone, UTC
from typing import List, Optional
from pydantic import UUID4
from azure.cosmos.exceptions import CosmosResourceNotFoundError, CosmosAccessConditionFailedError
from fastapi import HTTPException, status
from pydantic import parse_obj_as
from db.repositories.workspaces import WorkspaceRepository
from services.authentication import get_access_service
from models.domain.authentication import User
from db.errors import EntityDoesNotExist
from models.domain.airlock_request import AirlockFile, AirlockRequest, AirlockRequestStatus, \
    AirlockReview, AirlockReviewDecision, AirlockRequestHistoryItem, AirlockRequestType, AirlockReviewUserResource
from models.schemas.airlock_request import AirlockRequestInCreate, AirlockReviewInCreate
from core import config
from resources import strings
from db.repositories.base import BaseRepository
from services.logging import logger


class AirlockRequestRepository(BaseRepository):
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

    async def update_airlock_request_item(self, original_request: AirlockRequest, new_request: AirlockRequest, updated_by: User, request_properties: dict) -> AirlockRequest:
        history_item = AirlockRequestHistoryItem(
            resourceVersion=original_request.resourceVersion,
            updatedWhen=original_request.updatedWhen,
            updatedBy=original_request.updatedBy,
            properties=request_properties
        )
        new_request.history.append(history_item)

        # now update the request props
        new_request.resourceVersion = new_request.resourceVersion + 1
        new_request.updatedBy = updated_by
        new_request.updatedWhen = self.get_timestamp()

        await self.upsert_item_with_etag(new_request, new_request.etag)
        return new_request

    @staticmethod
    def airlock_requests_query():
        return 'SELECT * FROM c'

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

    def create_airlock_request_item(self, airlock_request_input: AirlockRequestInCreate, workspace_id: str, user) -> AirlockRequest:
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
            reviews=[]
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
        return parse_obj_as(List[AirlockRequest], airlock_requests)

    async def get_airlock_request_by_id(self, airlock_request_id: UUID4) -> AirlockRequest:
        try:
            airlock_requests = await self.read_item_by_id(str(airlock_request_id))
        except CosmosResourceNotFoundError:
            raise EntityDoesNotExist
        return parse_obj_as(AirlockRequest, airlock_requests)

    async def get_airlock_requests_for_airlock_manager(self, user: User, type: Optional[AirlockRequestType] = None, status: Optional[AirlockRequestStatus] = None, order_by: Optional[str] = None, order_ascending=True) -> List[AirlockRequest]:
        workspace_repo = await WorkspaceRepository.create()
        access_service = get_access_service()

        workspaces = await workspace_repo.get_active_workspaces()
        user_role_assignments = access_service.get_identity_role_assignments(user.id)

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
            updated_by: User,
            new_status: Optional[AirlockRequestStatus] = None,
            request_files: Optional[List[AirlockFile]] = None,
            status_message: Optional[str] = None,
            airlock_review: Optional[AirlockReview] = None,
            review_user_resource: Optional[AirlockReviewUserResource] = None) -> AirlockRequest:
        updated_request = self._build_updated_request(
            original_request=original_request,
            new_status=new_status,
            request_files=request_files,
            status_message=status_message,
            airlock_review=airlock_review,
            review_user_resource=review_user_resource,
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
            updated_by: Optional[User] = None) -> AirlockRequest:
        updated_request = copy.deepcopy(original_request)

        if new_status is not None:
            self._validate_status_update(current_status=original_request.status, new_status=new_status)
            updated_request.status = new_status

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
            updated_request.reviewUserResources[updated_by.id] = review_user_resource

        return updated_request

    def _validate_status_update(self, current_status, new_status):
        if not self.validate_status_update(current_status=current_status, new_status=new_status):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.AIRLOCK_REQUEST_ILLEGAL_STATUS_CHANGE)

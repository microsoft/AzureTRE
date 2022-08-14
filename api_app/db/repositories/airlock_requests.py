import copy
import uuid

from datetime import datetime
from typing import List
from pydantic import UUID4
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.cosmos import CosmosClient
from starlette import status
from fastapi import HTTPException
from pydantic import parse_obj_as
from models.domain.authentication import User
from db.errors import EntityDoesNotExist
from db.repositories.airlock_resources import AirlockResourceRepository
from models.domain.airlock_request import AirlockRequest, AirlockRequestStatus, AirlockRequestType
from models.schemas.airlock_request import AirlockRequestInCreate
from resources import strings


class AirlockRequestRepository(AirlockResourceRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)

    @staticmethod
    def airlock_requests_query():
        return 'SELECT * FROM c WHERE c.resourceType = "airlock-request"'

    def validate_status_update(self, current_status: AirlockRequestStatus, new_status: AirlockRequestStatus):
        # Cannot change status from approved
        approved_condition = current_status != AirlockRequestStatus.Approved
        # Cannot change status from rejected
        rejected_condition = current_status != AirlockRequestStatus.Rejected
        # Cannot change status from blocked
        blocked_condition = current_status != AirlockRequestStatus.Blocked

        # If approved-in-progress can only be changed to approved
        approved_in_progress_condition = current_status == AirlockRequestStatus.ApprovalInProgress and new_status == AirlockRequestStatus.Approved
        # If rejection-in-progress can only be changed to rejected
        rejected_in_progress_condition = current_status == AirlockRequestStatus.RejectionInProgress and new_status == AirlockRequestStatus.Rejected
        # If blocking-in-progress can only be changed to blocked
        blocking_in_progress_condition = current_status == AirlockRequestStatus.BlockingInProgress and new_status == AirlockRequestStatus.Blocked

        # If draft can only be changed to submitted
        draft_condition = current_status == AirlockRequestStatus.Draft and new_status == AirlockRequestStatus.Submitted
        # If submitted needs to get scanned first, which will change the status to either in-review or blocking-in-progress. but if scanner is disabled, it can go straight to in review
        submit_condition = current_status == AirlockRequestStatus.Submitted and (new_status == AirlockRequestStatus.InReview or new_status == AirlockRequestStatus.BlockingInProgress)
        # If in review can only be changed to either approve in progress or rejected in progress
        in_review_condition = current_status == AirlockRequestStatus.InReview and (new_status == AirlockRequestStatus.ApprovalInProgress or new_status == AirlockRequestStatus.RejectionInProgress)
        # Cancel is allowed only if the request is not actively changing, i.e. it is currently in draft or in review
        cancel_condition = (current_status == AirlockRequestStatus.Draft or current_status == AirlockRequestStatus.InReview) and new_status == AirlockRequestStatus.Cancelled
        # Failed is allowed from any non-final status
        failed_condition = (current_status == AirlockRequestStatus.Draft
                            or current_status == AirlockRequestStatus.Submitted
                            or current_status == AirlockRequestStatus.InReview
                            or current_status == AirlockRequestStatus.ApprovalInProgress
                            or current_status == AirlockRequestStatus.RejectionInProgress
                            or current_status == AirlockRequestStatus.BlockingInProgress) and new_status == AirlockRequestStatus.Failed

        return approved_condition and rejected_condition and blocked_condition and (approved_in_progress_condition or rejected_in_progress_condition or blocking_in_progress_condition or draft_condition or submit_condition or in_review_condition or cancel_condition or failed_condition)

    def create_airlock_request_item(self, airlock_request_input: AirlockRequestInCreate, workspace_id: str) -> AirlockRequest:
        full_airlock_request_id = str(uuid.uuid4())

        resource_spec_parameters = {**self.get_airlock_request_spec_params()}

        airlock_request = AirlockRequest(
            id=full_airlock_request_id,
            workspaceId=workspace_id,
            businessJustification=airlock_request_input.businessJustification,
            requestType=airlock_request_input.requestType,
            creationTime=datetime.utcnow().timestamp(),
            properties=resource_spec_parameters
        )

        return airlock_request

    def get_airlock_requests(self, workspace_id: str, user_id: str = None, type: AirlockRequestType = None, status: AirlockRequestStatus = None) -> List[AirlockRequest]:
        query = self.airlock_requests_query() + f' AND c.workspaceId = "{workspace_id}"'

        # optional filters
        if user_id:
            query += ' AND c.user.id=@user_id'
        if status:
            query += ' AND c.status=@status'
        if type:
            query += ' AND c.requestType=@type'

        parameters = [
            {"name": "@user_id", "value": user_id},
            {"name": "@status", "value": status},
            {"name": "@type", "value": type},
        ]
        airlock_requests = self.query(query=query, parameters=parameters)
        return parse_obj_as(List[AirlockRequest], airlock_requests)

    def get_airlock_request_by_id(self, airlock_request_id: UUID4) -> AirlockRequest:
        try:
            airlock_requests = self.read_item_by_id(str(airlock_request_id))
        except CosmosResourceNotFoundError:
            raise EntityDoesNotExist
        return parse_obj_as(AirlockRequest, airlock_requests)

    def update_airlock_request_status(self, airlock_request: AirlockRequest, new_status: AirlockRequestStatus, user: User, error_message: str = None) -> AirlockRequest:
        current_status = airlock_request.status
        if self.validate_status_update(current_status, new_status):
            updated_request = copy.deepcopy(airlock_request)
            updated_request.status = new_status
            if new_status == AirlockRequestStatus.Failed:
                updated_request.errorMessage = error_message
            return self.update_airlock_resource_item(airlock_request, updated_request, user, {"previousStatus": current_status})
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.AIRLOCK_REQUEST_ILLEGAL_STATUS_CHANGE)

    def get_airlock_request_spec_params(self):
        return self.get_resource_base_spec_params()

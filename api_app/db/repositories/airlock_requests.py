import copy
import uuid
from pydantic import UUID4
from azure.cosmos import CosmosClient
from starlette import status
from fastapi import HTTPException
from pydantic import parse_obj_as
from models.domain.authentication import User
from db.errors import EntityDoesNotExist
from db.repositories.airlock_resources import AirlockResourceRepository
from models.domain.airlock_request import AirlockRequest, AirlockRequestStatus
from models.schemas.airlock_request import AirlockRequestInCreate
from resources import strings


class AirlockRequestRepository(AirlockResourceRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)

    def _validate_status_update(self, current_status: AirlockRequestStatus, new_status: AirlockRequestStatus):
        # Cannot change status from approved
        approved_condition = current_status != AirlockRequestStatus.Approved
        # Cannot change status from rejected
        rejected_condition = current_status != AirlockRequestStatus.Rejected
        # Cannot change status from blocked
        blocked_condition = current_status != AirlockRequestStatus.Blocked
        # If approved in progress can only be changed to approved
        approved_in_progress_condition = current_status == AirlockRequestStatus.ApprovalInProgress and new_status == AirlockRequestStatus.Approved
        # If rejection in progress can only be changed to rejected
        rejected_in_progress_condition = current_status == AirlockRequestStatus.RejectionInProgress and new_status == AirlockRequestStatus.Rejected
        # If blocking in progress can only be changed to blocked
        blocking_in_progress_condition = current_status == AirlockRequestStatus.BlockingInProgress and new_status == AirlockRequestStatus.Blocked
        # If draft can only be changed to submitted
        draft_condition = current_status == AirlockRequestStatus.Draft and new_status == AirlockRequestStatus.Submitted
        # If submitted needs to get scanned first, but if scanner is disabled, it can go straight to in review
        # Note: since the scanner and the blob created triggers might race, it is possible that we skip the wait for scan status.
        submit_condition = current_status == AirlockRequestStatus.Submitted and (new_status == AirlockRequestStatus.InReview or new_status == AirlockRequestStatus.WaitForScan or new_status == AirlockRequestStatus.ScanInProgress)
        # If in review can only be changed to either approve in progress or rejected in progress
        in_review_condition = current_status == AirlockRequestStatus.InReview and new_status == AirlockRequestStatus.ApprovalInProgress or new_status == AirlockRequestStatus.RejectionInProgress
        # If in scan-in-progress can only be changed to either in review or blocking in progress
        scan_in_progress_condition = current_status == AirlockRequestStatus.ScanInProgress and new_status == AirlockRequestStatus.InReview or new_status == AirlockRequestStatus.BlockingInProgress
        # Cancel is allowed only if the request is not actively changing, i.e. it is currently in draft or in review
        cancel_condition = (current_status == AirlockRequestStatus.Draft or current_status == AirlockRequestStatus.InReview) and new_status == AirlockRequestStatus.Cancelled

        return approved_condition and rejected_condition and blocked_condition and (approved_in_progress_condition or rejected_in_progress_condition or blocking_in_progress_condition or draft_condition or submit_condition or in_review_condition or scan_in_progress_condition or cancel_condition)

    def create_airlock_request_item(self, airlock_request_input: AirlockRequestInCreate, workspace_id: str) -> AirlockRequest:
        full_airlock_request_id = str(uuid.uuid4())

        resource_spec_parameters = {**self.get_airlock_request_spec_params()}

        airlock_request = AirlockRequest(
            id=full_airlock_request_id,
            workspaceId=workspace_id,
            businessJustification=airlock_request_input.businessJustification,
            requestType=airlock_request_input.requestType,
            properties=resource_spec_parameters
        )

        return airlock_request

    def get_airlock_request_by_id(self, airlock_request_id: UUID4) -> AirlockRequest:
        airlock_requests = self.read_item_by_id(str(airlock_request_id))
        if not airlock_requests:
            raise EntityDoesNotExist
        return parse_obj_as(AirlockRequest, airlock_requests)

    def update_airlock_request_status(self, airlock_request: AirlockRequest, new_status: AirlockRequestStatus, user: User) -> AirlockRequest:
        current_status = airlock_request.status
        if self._validate_status_update(current_status, new_status):
            updated_request = copy.deepcopy(airlock_request)
            updated_request.status = new_status
            return self.update_airlock_resource_item(airlock_request, updated_request, user, {"previousStatus": current_status})
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.AIRLOCK_REQUEST_ILLEGAL_STATUS_CHANGE)

    def get_airlock_request_spec_params(self):
        return self.get_resource_base_spec_params()

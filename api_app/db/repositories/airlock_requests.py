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
        # Cannot change status from ready
        ready_condition = current_status != AirlockRequestStatus.Ready
        # Cannot change status from failed
        failed_condition = current_status != AirlockRequestStatus.Failed
        # Cannot change status from declined
        declined_condition = current_status != AirlockRequestStatus.Declined
        # If approved can only be changed to ready
        approved_condition = current_status == AirlockRequestStatus.Approved and new_status == AirlockRequestStatus.Ready
        # If rejected can only be changed to declined
        rejected_condition = current_status == AirlockRequestStatus.Rejected and new_status == AirlockRequestStatus.Declined
        # If blocked can only be changed to failed
        blocked_condition = current_status == AirlockRequestStatus.Blocked and new_status == AirlockRequestStatus.Failed
        # If draft can only be changed to submitted
        draft_condition = current_status == AirlockRequestStatus.Draft and new_status == AirlockRequestStatus.Submitted
        # If submitted needs to get scanned first, but if scanner is disabled, it can go straight to in review
        submit_condition = current_status == AirlockRequestStatus.Submitted and (new_status == AirlockRequestStatus.InReview or new_status == AirlockRequestStatus.InScan)
        # If in review can only be changed to either approve or rejected
        in_review_condition = current_status == AirlockRequestStatus.InReview and new_status == AirlockRequestStatus.Approved or new_status == AirlockRequestStatus.Rejected
        # If in scan can only be changed to either in review or blocked
        in_scan_condition = current_status == AirlockRequestStatus.InScan and new_status == AirlockRequestStatus.InReview or new_status == AirlockRequestStatus.Blocked
        # Cancel is allowed only if the request is not actively changing, i.e. it is currently in draft or in review
        cancel_condition = (current_status == AirlockRequestStatus.Draft or current_status == AirlockRequestStatus.InReview) and new_status == AirlockRequestStatus.Cancelled

        return ready_condition and failed_condition and declined_condition and (approved_condition or rejected_condition or blocked_condition or draft_condition or submit_condition or in_review_condition or in_scan_condition or cancel_condition)

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

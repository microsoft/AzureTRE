import copy
import uuid
from pydantic import UUID4
from azure.cosmos import CosmosClient
from starlette import status
from fastapi import HTTPException
from pydantic import parse_obj_as
from models.domain.authentication import User
from db.errors import EntityDoesNotExist
from models.domain.airlock_resource import AirlockRequestStatus
from db.repositories.airlock_resources import AirlockResourceRepository
from models.domain.airlock_request import AirlockRequest
from models.schemas.airlock_request import AirlockRequestInCreate
from resources import strings


class AirlockRequestRepository(AirlockResourceRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)

    def _validate_status_update(self, current_status: AirlockRequestStatus, new_status: AirlockRequestStatus):
        # Cannot change status from block
        blocked_condition = current_status != AirlockRequestStatus.Blocked
        # Cannot change status from approved
        approved_condition = current_status != AirlockRequestStatus.Approved
        # Cannot change status from rejected
        rejected_condition = current_status != AirlockRequestStatus.Rejected
        # If draft can only be changed to submitted
        draft_condition = current_status == AirlockRequestStatus.Draft and new_status == AirlockRequestStatus.Submitted
        # If submitted needs to get a review first
        submit_condition = current_status == AirlockRequestStatus.Submitted and new_status == AirlockRequestStatus.InReview
        # If in review can only be changed to either approve or rejected
        in_review_condition = current_status == AirlockRequestStatus.InReview and new_status == AirlockRequestStatus.Approved or new_status == AirlockRequestStatus.Rejected

        return blocked_condition and approved_condition and rejected_condition and (draft_condition or submit_condition or in_review_condition)

    def create_airlock_request_item(self, airlock_request_input: AirlockRequestInCreate, workspace_id: str) -> AirlockRequest:
        full_airlock_request_id = str(uuid.uuid4())

        # TODO - validate the request https://github.com/microsoft/AzureTRE/issues/2016
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
            return self.update_airlock_resource_item(airlock_request, updated_request, user)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.AIRLOCK_REQUEST_ILLEGAL_STATUS_CHANGE)

    def get_airlock_request_spec_params(self):
        return self.get_resource_base_spec_params()

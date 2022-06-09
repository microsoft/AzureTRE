import copy
import uuid
from azure.cosmos import CosmosClient
from pydantic import parse_obj_as
from models.domain.authentication import User
from db.errors import EntityDoesNotExist
from models.domain.airlock_resource import AirlockResourceType
from db.repositories.airlock_resources import AirlockResourceRepository
from models.domain.airlock_request import AirlockRequest, AirlockRequestStatus
from models.schemas.airlock_request import AirlockRequestInCreate


class AirlockRequestRepository(AirlockResourceRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)

    @staticmethod
    def airlock_request_query_string():
        return f'SELECT * FROM c WHERE c.resourceType = "{AirlockResourceType.AirlockRequest}"'

    def create_airlock_request_item(self, airlock_request_input: AirlockRequestInCreate, workspace_id: str) -> AirlockRequest:
        full_airlock_request_id = str(uuid.uuid4())

        # TODO - validate
        resource_spec_parameters = {**self.get_airlock_request_spec_params()}

        airlock_request = AirlockRequest(
            id=full_airlock_request_id,
            workspaceId=workspace_id,
            business_justification=airlock_request_input.business_justification,
            requestType=airlock_request_input.requestType,
            properties=resource_spec_parameters
        )

        return airlock_request

    def get_airlock_request_by_id(self, airlock_request_id: str) -> AirlockRequest:
        query = self.airlock_request_query_string() + f' AND c.id = "{airlock_request_id}"'
        airlock_requests = self.query(query=query)
        if not airlock_requests:
            raise EntityDoesNotExist
        return parse_obj_as(AirlockRequest, airlock_requests[0])

    def update_airlock_request_status(self, airlock_request: AirlockRequest, status: AirlockRequestStatus, user: User) -> AirlockRequest:
        updated_request = copy.deepcopy(airlock_request)
        updated_request.status = status

        return self.update_airlock_resource_item(airlock_request, updated_request, user)

    def get_airlock_request_spec_params(self):
        return self.get_resource_base_spec_params()

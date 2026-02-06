import pytest
from models.schemas.airlock_request import AirlockRequestAndOperationInResponse, get_sample_airlock_request
from models.schemas.operation import get_sample_operation

def test_airlock_request_and_operation_in_response_schema_is_valid():
    workspace_id = "933ad738-7265-4b5f-9eae-a1a62928772e"
    airlock_request_id = "121e921f-a4aa-44b3-90a9-e8da030495ef"
    operation_id = "121e921f-a4aa-44b3-90a9-e8da030495ef"

    sample_data = {
        "airlockRequest": get_sample_airlock_request(workspace_id, airlock_request_id),
        "operation": get_sample_operation(operation_id)
    }

    # This validates the schema extra example logic
    response = AirlockRequestAndOperationInResponse(**sample_data)
    assert response.airlockRequest.id == airlock_request_id
    assert response.operation.id == operation_id

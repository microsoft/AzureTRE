import pytest
from pydantic import ValidationError

from models.schemas.airlock_request import AirlockRequestAndOperationInResponse, AirlockRequestInCreate, AirlockReviewInCreate, get_sample_airlock_request
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


def test_airlock_request_in_create_requires_type():
    with pytest.raises(ValidationError):
        AirlockRequestInCreate(title="a request title", businessJustification="some business justification")


def test_airlock_review_in_create_requires_approval():
    with pytest.raises(ValidationError):
        AirlockReviewInCreate(decisionExplanation="the reason why this request was approved/rejected")


def test_airlock_review_in_create_openapi_example_uses_boolean_approval():
    example = AirlockReviewInCreate.model_config["json_schema_extra"]["example"]

    assert isinstance(example["approval"], bool)
    assert example["approval"] is True

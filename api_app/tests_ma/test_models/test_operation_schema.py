import pytest
from models.domain.operation import Operation
from models.schemas.operation import get_sample_operation, OperationInResponse, OperationInList

def test_get_sample_operation_is_valid():
    operation_id = "7ac667f0-fd3f-4a6c-815b-82d0cb7a2132"
    sample_operation_dict = get_sample_operation(operation_id)

    # This will raise a ValidationError if the dictionary doesn't match the Operation model
    operation = Operation(**sample_operation_dict)

    assert operation.id == operation_id
    assert len(operation.steps) > 0
    assert operation.steps[0].templateStepId == "main"

def test_operation_in_response_schema_is_valid():
    operation_id = "7ac667f0-fd3f-4a6c-815b-82d0cb7a2132"
    sample_data = {
        "operation": get_sample_operation(operation_id)
    }
    # This validates the schema extra example logic
    response = OperationInResponse(**sample_data)
    assert response.operation.id == operation_id

def test_operation_in_list_schema_is_valid():
    operation_id = "7ac667f0-fd3f-4a6c-815b-82d0cb7a2132"
    sample_data = {
        "operations": [get_sample_operation(operation_id)]
    }
    # This validates the schema extra example logic
    op_list = OperationInList(**sample_data)
    assert len(op_list.operations) == 1
    assert op_list.operations[0].id == operation_id

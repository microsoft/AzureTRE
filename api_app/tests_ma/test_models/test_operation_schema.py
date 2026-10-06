from models.domain.operation import Operation, Status
from models.domain.resource_template import PipelineStepProperty
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


def test_operation_omitted_status_uses_enum_default():
    operation = Operation(
        id="operation-id",
        resourceId="resource-id",
        resourcePath="/workspaces/resource-id",
        action="install",
        user={},
    )

    assert isinstance(operation.status, Status)
    assert operation.status == Status.AwaitingDeployment


def test_operation_omitted_timestamps_use_float_defaults():
    operation = Operation(
        id="operation-id",
        resourceId="resource-id",
        resourcePath="/workspaces/resource-id",
        status=Status.AwaitingDeployment,
        action="install",
        user={},
    )

    assert isinstance(operation.createdWhen, float)
    assert isinstance(operation.updatedWhen, float)


def test_pipeline_step_property_value_defaults_to_none_when_omitted():
    step_property = PipelineStepProperty(name="target_property", type="string")

    assert step_property.value is None

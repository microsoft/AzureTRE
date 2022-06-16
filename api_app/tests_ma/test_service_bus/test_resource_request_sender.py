import copy
import json
import pytest
import uuid

from azure.servicebus import ServiceBusMessage
from mock import AsyncMock, MagicMock, patch
from models.domain.resource_template import PipelineStep, PipelineStepProperty
from models.schemas.resource import ResourcePatch
from service_bus.helpers import (
    substitute_properties,
    substitute_value,
    try_upgrade_with_retries,
    update_resource_for_step,
)
from models.schemas.workspace_template import get_sample_workspace_template_object
from tests_ma.test_api.conftest import create_test_user
from tests_ma.test_service_bus.test_deployment_status_update import (
    create_sample_operation,
)
from models.domain.workspace_service import WorkspaceService
from models.domain.resource import Resource, ResourceType
from service_bus.resource_request_sender import (
    send_resource_request_message,
    RequestAction,
)
from azure.cosmos.exceptions import CosmosAccessConditionFailedError

pytestmark = pytest.mark.asyncio


def create_test_resource():
    return Resource(
        id=str(uuid.uuid4()),
        resourceType=ResourceType.Workspace,
        templateName="Test resource template name",
        templateVersion="2.718",
        etag="",
        properties={"testParameter": "testValue"},
        resourcePath="test",
    )


@pytest.mark.parametrize(
    "request_action", [RequestAction.Install, RequestAction.UnInstall]
)
@patch("service_bus.resource_request_sender.OperationRepository")
@patch("service_bus.helpers.ServiceBusClient")
@patch("service_bus.resource_request_sender.ResourceRepository")
@patch("service_bus.resource_request_sender.ResourceTemplateRepository")
async def test_resource_request_message_generated_correctly(
    resource_template_repo,
    resource_repo,
    service_bus_client_mock,
    operations_repo_mock,
    request_action,
):
    service_bus_client_mock().get_queue_sender().send_messages = AsyncMock()
    resource = create_test_resource()
    operation = create_sample_operation(resource.id, request_action)
    template = get_sample_workspace_template_object()
    operations_repo_mock.create_operation_item.return_value = operation
    resource_repo.get_resource_by_id.return_value = resource

    await send_resource_request_message(
        resource=resource,
        operations_repo=operations_repo_mock,
        resource_repo=resource_repo,
        user=create_test_user(),
        resource_template=template,
        resource_template_repo=resource_template_repo,
        action=request_action,
    )

    args = service_bus_client_mock().get_queue_sender().send_messages.call_args.args
    assert len(args) == 1
    assert isinstance(args[0], ServiceBusMessage)

    sent_message = args[0]
    assert sent_message.correlation_id == operation.id
    sent_message_as_json = json.loads(str(sent_message))
    assert sent_message_as_json["id"] == resource.id
    assert sent_message_as_json["action"] == request_action


@patch("service_bus.resource_request_sender.OperationRepository.create_operation_item")
@patch("service_bus.resource_request_sender.ResourceRepository")
@patch("service_bus.resource_request_sender.ResourceTemplateRepository")
async def test_multi_step_document_sends_first_step(
    resource_template_repo,
    resource_repo,
    create_op_item_mock,
    multi_step_operation,
    basic_shared_service,
    basic_shared_service_template,
    multi_step_resource_template,
    user_resource_multi,
    test_user,
):
    create_op_item_mock.return_value = multi_step_operation
    temp_workspace_service = WorkspaceService(
        id="123", templateName="template-name-here", templateVersion="0.1.0", etag=""
    )

    # return the primary resource, a 'parent' workspace service, then the shared service to patch
    resource_repo.get_resource_by_id.side_effect = [
        user_resource_multi,
        temp_workspace_service,
        basic_shared_service,
    ]
    resource_template_repo.get_current_template.side_effect = [
        multi_step_resource_template,
        basic_shared_service_template,
    ]

    resource_repo.patch_resource = MagicMock(
        return_value=(basic_shared_service, basic_shared_service_template)
    )

    resource_repo.get_resource_by_id = MagicMock(
        return_value=basic_shared_service
    )

    _ = update_resource_for_step(
        operation_step=multi_step_operation.steps[0],
        resource_repo=resource_repo,
        resource_template_repo=resource_template_repo,
        primary_resource_id="resource-id",
        resource_to_update_id=basic_shared_service.id,
        primary_action="install",
        user=test_user,
    )

    expected_patch = ResourcePatch(properties={"display_name": "new name"})

    # expect the patch for step 1
    resource_repo.patch_resource.assert_called_once_with(
        resource=basic_shared_service,
        resource_patch=expected_patch,
        resource_template=basic_shared_service_template,
        etag=basic_shared_service.etag,
        resource_template_repo=resource_template_repo,
        user=test_user,
    )


@patch("service_bus.resource_request_sender.ResourceRepository")
@patch("service_bus.resource_request_sender.ResourceTemplateRepository")
async def test_multi_step_document_retries(
    resource_template_repo,
    resource_repo,
    basic_shared_service,
    basic_shared_service_template,
    test_user,
):

    resource_repo.get_resource_by_id.return_value = basic_shared_service
    resource_template_repo.get_current_template.return_value = (
        basic_shared_service_template
    )

    # simulate an etag mismatch
    resource_repo.patch_resource = MagicMock(
        side_effect=CosmosAccessConditionFailedError
    )

    num_retries = 5
    try:
        try_upgrade_with_retries(
            num_retries=num_retries,
            attempt_count=0,
            resource_repo=resource_repo,
            resource_template_repo=resource_template_repo,
            properties={},
            user=test_user,
            resource_to_update_id="resource-id",
        )
    except CosmosAccessConditionFailedError:
        pass

    # check it tried to patch and re-get the item the first time + all the retries
    assert len(resource_repo.patch_resource.mock_calls) == (num_retries + 1)
    assert len(resource_repo.get_resource_by_id.mock_calls) == (num_retries + 1)


def test_substitution(primary_resource):
    resource_dict = primary_resource.dict()

    # single array val
    val_to_sub = "{{ resource.properties.address_prefix }}"
    val = substitute_value(val_to_sub, resource_dict)
    assert val == ["172.0.0.1", "192.168.0.1"]

    # array val to inject, with text. Text will be dropped.
    val_to_sub = "{{ resource.properties.fqdn }} - this text will be removed because fqdn is a list and shouldn't be concatenated into a string"
    val = substitute_value(val_to_sub, resource_dict)
    assert val == ["*pypi.org", "files.pythonhosted.org", "security.ubuntu.com"]

    # single string val, with text. Will be concatenated into text.
    val_to_sub = "I think {{ resource.templateName }} is the best template!"
    val = substitute_value(val_to_sub, resource_dict)
    assert val == "I think template name is the best template!"

    # multiple string vals, with text. Will be concatenated.
    val_to_sub = "I think {{ resource.templateName }} is the best template, and {{ resource.templateVersion }} is a good version!"
    val = substitute_value(val_to_sub, resource_dict)
    assert val == "I think template name is the best template, and 7 is a good version!"


def test_simple_substitution(simple_pipeline_step, primary_resource, resource_to_update):
    obj = substitute_properties(simple_pipeline_step, primary_resource, resource_to_update)

    assert obj['just_text'] == 'Updated by 123'
    assert obj['just_text_2'] == 'No substitution, just a fixed string here'
    assert obj['just_text_3'] == 'Multiple substitutions -> 123 and template name'


def test_substitution_props(pipeline_step, primary_resource, resource_to_update):
    obj = substitute_properties(pipeline_step, primary_resource, resource_to_update)

    assert obj["rule_collections"][0]["rules"][0]["target_fqdns"] == ["*pypi.org", "files.pythonhosted.org", "security.ubuntu.com"]
    assert obj["rule_collections"][0]["rules"][0]["source_addresses"] == ["172.0.0.1", "192.168.0.1"]
    assert obj["rule_collections"][0]["rules"][0]["protocols"][1]["type"] == "MyCoolProtocol"
    assert obj["rule_collections"][0]["rules"][0]["description"] == "Deployed by 123"


def test_substitution_array_append_remove(pipeline_step, primary_resource, resource_to_update):

    # do the first substitution, and assert there's a single rule collection
    step = copy.deepcopy(pipeline_step)
    step.properties[0].arraySubstitutionAction = "append"
    step.properties[0].value['name'] = "object 1"
    obj = substitute_properties(step, primary_resource, resource_to_update)
    assert len(obj["rule_collections"]) == 1

    # in effect the RP will do this:
    resource_to_update.properties = obj

    # now append another substitution, and check we've got both rules
    step = copy.deepcopy(pipeline_step)
    step.properties[0].arraySubstitutionAction = "append"
    step.properties[0].value['name'] = "object 2"
    obj = substitute_properties(step, primary_resource, resource_to_update)
    assert len(obj["rule_collections"]) == 2

    # the RP makes the change again...
    resource_to_update.properties = obj

    # now append another substitution, and check we've got all 3 rules
    step = copy.deepcopy(pipeline_step)
    step.properties[0].arraySubstitutionAction = "append"
    step.properties[0].value['name'] = "object 3"
    obj = substitute_properties(step, primary_resource, resource_to_update)
    assert len(obj["rule_collections"]) == 3

    # the RP makes the change again...
    resource_to_update.properties = obj

    # now remove object 2...
    step = copy.deepcopy(pipeline_step)
    step.properties[0].arraySubstitutionAction = "remove"
    step.properties[0].value['name'] = "object 2"
    obj = substitute_properties(step, primary_resource, resource_to_update)
    assert len(obj["rule_collections"]) == 2
    assert obj['rule_collections'][0]['name'] == "object 1"
    assert obj['rule_collections'][1]['name'] == "object 3"

    # the RP makes the change again...
    resource_to_update.properties = obj

    # now remove object 1...
    step = copy.deepcopy(pipeline_step)
    step.properties[0].arraySubstitutionAction = "remove"
    step.properties[0].value['name'] = "object 1"
    obj = substitute_properties(step, primary_resource, resource_to_update)
    assert len(obj["rule_collections"]) == 1
    assert obj['rule_collections'][0]['name'] == "object 3"

    # the RP makes the change again...
    resource_to_update.properties = obj

    # now remove object 3...
    step = copy.deepcopy(pipeline_step)
    step.properties[0].arraySubstitutionAction = "remove"
    step.properties[0].value['name'] = "object 3"
    obj = substitute_properties(step, primary_resource, resource_to_update)
    assert len(obj["rule_collections"]) == 0

    # the RP makes the change again...
    resource_to_update.properties = obj

    # now remove another one, even though the array is empty...
    step = copy.deepcopy(pipeline_step)
    step.properties[0].arraySubstitutionAction = "remove"
    step.properties[0].value['name'] = "object 1"
    obj = substitute_properties(step, primary_resource, resource_to_update)
    assert len(obj["rule_collections"]) == 0


def test_substitution_array_append_replace(pipeline_step, primary_resource, resource_to_update):

    # add object 1
    step = copy.deepcopy(pipeline_step)
    step.properties[0].arraySubstitutionAction = "append"
    step.properties[0].value['name'] = "Object 1"
    obj = substitute_properties(step, primary_resource, resource_to_update)
    assert len(obj["rule_collections"]) == 1
    assert obj["rule_collections"][0]["name"] == "Object 1"

    # the RP does this:
    resource_to_update.properties = obj

    # add object 2
    step = copy.deepcopy(pipeline_step)
    step.properties[0].arraySubstitutionAction = "append"
    step.properties[0].value['name'] = "Object 2"
    obj = substitute_properties(step, primary_resource, resource_to_update)
    assert len(obj["rule_collections"]) == 2
    assert obj["rule_collections"][1]["name"] == "Object 2"

    # the RP does this:
    resource_to_update.properties = obj

    # replace object 1
    step = copy.deepcopy(pipeline_step)
    step.properties[0].arraySubstitutionAction = "replace"
    step.properties[0].value['name'] = "Object 1"
    step.properties[0].value['action'] = "Deny Object 1"
    obj = substitute_properties(step, primary_resource, resource_to_update)
    assert len(obj["rule_collections"]) == 2
    assert obj["rule_collections"][0]["action"] == "Deny Object 1"

    # the RP does this:
    resource_to_update.properties = obj

    # replace the next one
    step = copy.deepcopy(pipeline_step)
    step.properties[0].arraySubstitutionAction = "replace"
    step.properties[0].value['name'] = "Object 2"
    step.properties[0].value['action'] = "Deny Object 2"
    obj = substitute_properties(step, primary_resource, resource_to_update)
    assert len(obj["rule_collections"]) == 2
    assert obj["rule_collections"][1]["action"] == "Deny Object 2"


def test_substitution_array_replace_not_found(pipeline_step, primary_resource, resource_to_update):

    # try to replace an item not there - it should just append
    step = copy.deepcopy(pipeline_step)
    step.properties[0].arraySubstitutionAction = "replace"
    step.properties[0].value['name'] = "Object 1"
    obj = substitute_properties(step, primary_resource, resource_to_update)
    assert len(obj["rule_collections"]) == 1
    assert obj["rule_collections"][0]["name"] == "Object 1"

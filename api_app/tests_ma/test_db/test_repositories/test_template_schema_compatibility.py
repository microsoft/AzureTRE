import copy
from unittest.mock import AsyncMock

import pytest
from jsonschema.exceptions import ValidationError

from db.repositories.resource_templates import ResourceTemplateRepository
from db.repositories.resources import ResourceRepository
from models.domain.resource import ResourceType
from models.schemas.resource import ResourcePatch
from models.schemas.resource_template import ResourceTemplateInCreate
from resources.strings import RESOURCE_ACTION_UPDATE


DIALECTS = [None, "http://json-schema.org/draft-07/schema", "https://json-schema.org/draft/2020-12/schema"]


async def register_and_reload(dialect, resource_type=ResourceType.WorkspaceService):
    schema = {
        "$id": "https://example.test/template.json",
        "$defs": {"label": {"type": "string", "minLength": 3}},
        "title": "Schema compatibility",
        "description": "Registration and resource validation regression fixture",
        "properties": {
            "fixed": {"type": "string", "updateable": False},
            "editable": {"$ref": "#/$defs/label", "updateable": True},
            "enabled": {"type": "boolean", "updateable": True},
        },
        "allOf": [{
            "if": {"properties": {"enabled": {"const": True}}, "required": ["enabled"]},
            "then": {"properties": {"conditional": {"type": "string"}}},
        }],
    }
    if dialect:
        schema["$schema"] = dialect
    template_input = ResourceTemplateInCreate(name="compatibility", version="1.0.0", current=True, json_schema=schema)
    repository = ResourceTemplateRepository()
    repository.save_item = AsyncMock()
    await repository.create_template(template_input, resource_type, "parent")
    saved_template = repository.save_item.call_args.args[0].model_dump(mode="json")
    repository.query = AsyncMock(return_value=[saved_template])
    reloaded = await repository.get_template_by_name_and_version("compatibility", "1.0.0", resource_type, "parent")
    assert reloaded.model_dump().get("$schema") == dialect
    assert reloaded.model_dump()["$defs"] == schema["$defs"]
    return repository, reloaded


@pytest.mark.asyncio
@pytest.mark.parametrize("dialect", DIALECTS)
@pytest.mark.parametrize("resource_type", list(ResourceType))
async def test_registered_templates_preserve_create_and_patch_restrictions(dialect, resource_type):
    template_repo, template = await register_and_reload(dialect, resource_type)
    resources = ResourceRepository()
    enriched = template_repo.enrich_template(template)
    original = copy.deepcopy(enriched)
    valid = {"display_name": "Example", "description": "Example", "fixed": "original", "editable": "valid"}

    resources._validate_resource_parameters({"properties": valid}, enriched)
    with pytest.raises(ValidationError, match="unexpected"):
        resources._validate_resource_parameters({"properties": {**valid, "unexpected": "value"}}, enriched)
    with pytest.raises(ValidationError):
        resources._validate_resource_parameters({"properties": {**valid, "editable": "x"}}, enriched)

    resources.validate_patch(ResourcePatch(properties={"editable": "changed"}), template_repo, template, RESOURCE_ACTION_UPDATE)
    for properties in [{"fixed": "changed"}, {"unexpected": "value"}, {"editable": "x"}]:
        with pytest.raises(ValidationError):
            resources.validate_patch(ResourcePatch(properties=properties), template_repo, template, RESOURCE_ACTION_UPDATE)
    assert enriched == original


@pytest.mark.asyncio
@pytest.mark.parametrize("dialect", DIALECTS)
async def test_registered_templates_allow_only_active_conditional_properties(dialect):
    template_repo, template = await register_and_reload(dialect)
    enriched = template_repo.enrich_template(template)
    properties = {"display_name": "Example", "description": "Example", "enabled": True, "conditional": "allowed"}
    ResourceRepository._validate_resource_parameters({"properties": properties}, enriched)
    with pytest.raises(ValidationError, match="conditional"):
        ResourceRepository._validate_resource_parameters({"properties": {**properties, "enabled": False}}, enriched)


def test_draft7_keeps_legacy_dependency_validation():
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {"settings": {
            "type": "object",
            "properties": {"first": {"type": "string"}, "second": {"type": "string"}},
            "dependencies": {"first": ["second"]},
        }},
        "unevaluatedProperties": False,
    }
    ResourceRepository._validate_resource_parameters({"properties": {"settings": {"first": "a", "second": "b"}}}, schema)
    with pytest.raises(ValidationError, match="dependency"):
        ResourceRepository._validate_resource_parameters({"properties": {"settings": {"first": "a"}}}, schema)

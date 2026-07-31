import pytest
from jsonschema import validate
from mock import patch, call

import services.schema_service


@patch('services.schema_service.read_schema')
@patch('services.schema_service.enrich_template')
def test_enrich_workspace_template_enriches_with_workspace_defaults_and_aad(enrich_template_mock, read_schema_mock, basic_resource_template):
    workspace_template = basic_resource_template
    # read schema called twice - once for default props and once for aad
    default_props = (['description'], {'description': {'type': 'string'}})
    aad_props = (['client_id'], {'client_id': {'type': 'string'}})
    read_schema_mock.side_effect = [default_props, aad_props]

    services.schema_service.enrich_workspace_template(workspace_template)

    read_schema_mock.assert_has_calls([call('workspace.json'), call('azuread.json')])
    enrich_template_mock.assert_called_once_with(workspace_template, [default_props, aad_props], is_update=False)


@patch('services.schema_service.read_schema')
@patch('services.schema_service.enrich_template')
def test_enrich_workspace_service_template_enriches_with_workspace_service_defaults(enrich_template_mock, read_schema_mock, basic_resource_template):
    workspace_service_template = basic_resource_template
    default_props = (['description'], {'description': {'type': 'string'}})
    read_schema_mock.return_value = default_props

    services.schema_service.enrich_workspace_service_template(workspace_service_template)

    read_schema_mock.assert_called_once_with('workspace_service.json')
    enrich_template_mock.assert_called_once_with(workspace_service_template, [default_props], is_update=False)


@patch('services.schema_service.read_schema')
@patch('services.schema_service.enrich_template')
def test_enrich_user_resource_template_enriches_with_user_resource_defaults(enrich_template_mock, read_schema_mock, basic_user_resource_template):
    user_resource_template = basic_user_resource_template
    default_props = (['description'], {'description': {'type': 'string'}})
    read_schema_mock.return_value = default_props

    services.schema_service.enrich_user_resource_template(user_resource_template)

    read_schema_mock.assert_called_once_with('user_resource.json')
    enrich_template_mock.assert_called_once_with(user_resource_template, [default_props], is_update=False)


@pytest.mark.parametrize('original, extra1, extra2, expected', [
    # basic scenario
    (
        {'num_vms': {'type': 'string'}},
        {'description': {'type': 'string'}, 'display_name': {'type': 'string'}},
        {'client_id': {'type': 'string'}},
        {'num_vms': {'type': 'string'}, 'description': {'type': 'string'}, 'display_name': {'type': 'string'}, 'client_id': {'type': 'string'}}
    ),
    # empty original
    (
        {},
        {'description': {'type': 'string'}, 'display_name': {'type': 'string'}},
        {'client_id': {'type': 'string'}},
        {'description': {'type': 'string'}, 'display_name': {'type': 'string'}, 'client_id': {'type': 'string'}}
    ),
    # duplicates
    (
        {'description': {'type': 'string'}},
        {'description': {'type': 'string'}, 'display_name': {'type': 'string'}},
        {'client_id': {'type': 'string'}},
        {'description': {'type': 'string'}, 'display_name': {'type': 'string'}, 'client_id': {'type': 'string'}}
    ),
    # duplicate names - different defaults
    (
        {'description': {'type': 'string', 'default': 'service description'}, 'display_name': {'type': 'string'}},
        {'description': {'type': 'string', 'default': ''}},
        {'client_id': {'type': 'string'}},
        {'description': {'type': 'string', 'default': 'service description'}, 'display_name': {'type': 'string'}, 'client_id': {'type': 'string'}}
    )])
def test_enrich_template_combines_properties(original, extra1, extra2, expected, basic_resource_template):
    original_template = basic_resource_template
    original_template.properties = original

    template = services.schema_service.enrich_template(original_template, [([], extra1), ([], extra2)])

    assert template['properties'] == expected


@pytest.mark.parametrize('original, extra1, extra2, expected', [
    # basic scenario
    (
        ['num_vms'],
        ['description', 'display_name'],
        ['client_id'],
        ['num_vms', 'description', 'display_name', 'client_id']
    ),
    # empty original
    (
        [],
        ['description', 'display_name'],
        ['client_id'],
        ['description', 'display_name', 'client_id']
    ),
    # duplicates
    (
        ['description'],
        ['description', 'display_name'],
        ['client_id'],
        ['description', 'display_name', 'client_id']
    )])
def test_enrich_template_combines_required(original, extra1, extra2, expected, basic_resource_template):
    original_template = basic_resource_template
    original_template.required = original

    template = services.schema_service.enrich_template(original_template, [(extra1, {}), (extra2, {})])

    # test that the list contents are expected (sorting doesn't matter)
    actual = template['required']
    assert len(actual) == len(expected)
    for item in expected:
        assert item in actual


def test_enrich_template_adds_system_properties(basic_resource_template):
    original_template = basic_resource_template

    template = services.schema_service.enrich_template(original_template, [])

    assert 'tre_id' in template['system_properties']


def test_enrich_template_removes_invalid_legacy_null_property_fields(basic_resource_template):
    basic_resource_template.properties = {
        "os_image": {
            "type": "string",
            "items": None,
            "properties": None,
            "enum": None,
            "pattern": None,
            "default": None,
            "const": None,
        }
    }

    template = services.schema_service.enrich_template(basic_resource_template, [])

    assert "items" not in template["properties"]["os_image"]
    assert "properties" not in template["properties"]["os_image"]
    assert "enum" not in template["properties"]["os_image"]
    assert "pattern" not in template["properties"]["os_image"]
    assert "default" not in template["properties"]["os_image"]
    assert "const" not in template["properties"]["os_image"]
    validate(instance={"os_image": "Windows Server 2025"}, schema=template)


def test_enrich_template_removes_invalid_legacy_null_property_fields_recursively(basic_resource_template):
    basic_resource_template.properties = {
        "vm_config": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "vm_size": {
                        "type": "string",
                        "items": None,
                        "enum": ["Standard_D2_v3"]
                    }
                }
            }
        }
    }
    basic_resource_template.allOf = [{
        "if": {
            "properties": {
                "assign_to_another_user": {
                    "const": True
                }
            }
        },
        "then": {
            "properties": {
                "owner_id": {
                    "type": "string",
                    "pattern": None,
                    "minLength": 1
                }
            }
        }
    }]

    template = services.schema_service.enrich_template(basic_resource_template, [])

    assert "items" not in template["properties"]["vm_config"]["items"]["properties"]["vm_size"]
    assert "pattern" not in template["allOf"][0]["then"]["properties"]["owner_id"]
    validate(instance={"vm_config": [{"vm_size": "Standard_D2_v3"}]}, schema=template)


def test_enrich_template_adds_read_only_on_update(basic_resource_template):
    original_template = basic_resource_template

    template = services.schema_service.enrich_template(original_template, [], is_update=True)

    assert "readOnly" not in template["properties"]["updateable_property"].keys()
    assert template["properties"]["fixed_property"]["readOnly"] is True

import pytest
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


def test_enrich_template_adds_read_only_on_update(basic_resource_template):
    original_template = basic_resource_template

    template = services.schema_service.enrich_template(original_template, [], is_update=True)

    assert "readOnly" not in template["properties"]["updateable_property"].keys()
    assert template["properties"]["fixed_property"]["readOnly"] is True

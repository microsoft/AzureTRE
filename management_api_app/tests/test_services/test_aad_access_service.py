import pytest
from mock import patch

from services.aad_access_service import AADAccessService
from services.access_service import AuthConfigValidationError


def test_extract_workspace__raises_error_if_app_id_not_available():
    access_service = AADAccessService()
    with pytest.raises(AuthConfigValidationError):
        access_service.extract_workspace_auth_information(data={})


@patch("services.aad_access_service.AADAccessService._get_app_auth_info", return_value={"roles": {"TREResearcher": "1234"}})
def test_extract_workspace__raises_error_if_owner_not_in_roles(get_app_auth_info_mock):
    access_service = AADAccessService()
    with pytest.raises(AuthConfigValidationError):
        access_service.extract_workspace_auth_information(data={"app_id": "1234"})


@patch("services.aad_access_service.AADAccessService._get_app_auth_info", return_value={"roles": {"TREOwner": "1234"}})
def test_extract_workspace__raises_error_if_researcher_not_in_roles(get_app_auth_info_mock):
    access_service = AADAccessService()
    with pytest.raises(AuthConfigValidationError):
        access_service.extract_workspace_auth_information(data={"app_id": "1234"})


@patch("services.aad_access_service.AADAccessService._get_app_sp_graph_data", return_value={})
def test_extract_workspace__raises_error_if_graph_data_is_invalid(get_app_sp_graph_data_mock):
    access_service = AADAccessService()
    with pytest.raises(AuthConfigValidationError):
        access_service.extract_workspace_auth_information(data={"app_id": "1234"})


@patch("services.aad_access_service.AADAccessService._get_app_sp_graph_data")
def test_extract_workspace__returns_sp_id_and_roles(get_app_sp_graph_data_mock):
    get_app_sp_graph_data_mock.return_value = {
        'value': [
            {
                'id': '12345',
                'appRoles': [
                    {'id': '1abc3', 'value': 'TREResearcher'},
                    {'id': '1abc4', 'value': 'TREOwner'},
                ]
            }
        ]
    }
    expected_auth_info = {
        'sp_id': '12345',
        'roles': {'TREResearcher': '1abc3', 'TREOwner': '1abc4'}
    }

    access_service = AADAccessService()
    actual_auth_info = access_service.extract_workspace_auth_information(data={"app_id": "1234"})

    assert actual_auth_info == expected_auth_info

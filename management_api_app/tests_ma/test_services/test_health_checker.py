from mock import patch
from azure.core.exceptions import ServiceRequestError

from models.schemas.status import StatusEnum
from resources import strings
from services import health_checker


@patch("services.health_checker.CosmosClient")
def test_get_state_store_status_responding(cosmos_client_mock) -> None:
    cosmos_client_mock.return_value = None

    status, message = health_checker.create_state_store_status()

    assert status == StatusEnum.ok
    assert message == ""


@patch("services.health_checker.CosmosClient")
def test_get_state_store_status_not_responding(cosmos_client_mock) -> None:
    cosmos_client_mock.return_value = None
    cosmos_client_mock.side_effect = ServiceRequestError(message="some message")

    status, message = health_checker.create_state_store_status()

    assert status == StatusEnum.not_ok
    assert message == strings.STATE_STORE_ENDPOINT_NOT_RESPONDING


@patch("services.health_checker.CosmosClient")
def test_get_state_store_status_other_exception(cosmos_client_mock) -> None:
    cosmos_client_mock.return_value = None
    cosmos_client_mock.side_effect = Exception()

    status, message = health_checker.create_state_store_status()

    assert status == StatusEnum.not_ok
    assert message == strings.UNSPECIFIED_ERROR

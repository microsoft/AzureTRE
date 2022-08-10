from fastapi import HTTPException, status
import pytest

from resources import strings
from services.airlock import validate_user_allowed_to_access_storage_account, get_required_permission, \
    validate_request_status
from models.domain.airlock_resource import AirlockResourceType
from models.domain.airlock_request import AirlockRequest, AirlockRequestStatus, AirlockRequestType
from tests_ma.test_api.conftest import create_workspace_owner_user, create_workspace_researcher_user


def sample_airlock_request(status=AirlockRequestStatus.Draft):
    airlock_request = AirlockRequest(
        id="AIRLOCK_REQUEST_ID",
        resourceType=AirlockResourceType.AirlockRequest,
        workspaceId="WORKSPACE_ID",
        requestType=AirlockRequestType.Import,
        files=[],
        businessJustification="some test reason",
        status=status
    )
    return airlock_request


def test_validate_user_is_allowed_to_access_sa_blocks_access_as_expected():
    # Workspace owner can access only in review
    ws_owner_user = create_workspace_owner_user()
    draft_airlock_request = sample_airlock_request()
    with pytest.raises(HTTPException) as ex:
        validate_user_allowed_to_access_storage_account(
            user=ws_owner_user,
            airlock_request=draft_airlock_request
        )

    assert ex.value.status_code == status.HTTP_403_FORBIDDEN

    researcher_user = create_workspace_researcher_user()
    review_airlock_request = sample_airlock_request(AirlockRequestStatus.InReview)
    with pytest.raises(HTTPException) as ex:
        validate_user_allowed_to_access_storage_account(
            user=researcher_user,
            airlock_request=review_airlock_request
        )

    assert ex.value.status_code == status.HTTP_403_FORBIDDEN


def test_validate_user_is_allowed_to_access_grants_access_to_user_with_a_valid_role():
    # Workspace owner can access only in review
    ws_owner_user = create_workspace_owner_user()
    draft_airlock_request = sample_airlock_request(AirlockRequestStatus.InReview)

    assert (validate_user_allowed_to_access_storage_account(
        user=ws_owner_user,
        airlock_request=draft_airlock_request) is None)

    researcher_user = create_workspace_researcher_user()
    review_airlock_request = sample_airlock_request(AirlockRequestStatus.Approved)
    assert (
        validate_user_allowed_to_access_storage_account(
            user=researcher_user,
            airlock_request=review_airlock_request
        ) is None)


@pytest.mark.parametrize('airlock_status',
                         [AirlockRequestStatus.ApprovalInProgress,
                          AirlockRequestStatus.RejectionInProgress,
                          AirlockRequestStatus.BlockingInProgress])
def test_validate_request_status_raises_error_for_in_progress_request(airlock_status):
    airlock_request = sample_airlock_request(airlock_status)
    with pytest.raises(HTTPException) as ex:
        validate_request_status(airlock_request)

    assert ex.value.status_code == status.HTTP_400_BAD_REQUEST
    assert ex.value.detail == strings.AIRLOCK_REQUEST_IN_PROGRESS


def test_validate_request_status_raises_error_for_canceled_request():
    airlock_request = sample_airlock_request(AirlockRequestStatus.Cancelled)
    with pytest.raises(HTTPException) as ex:
        validate_request_status(airlock_request)

    assert ex.value.status_code == status.HTTP_400_BAD_REQUEST
    assert ex.value.detail == strings.AIRLOCK_REQUEST_IS_CANCELED


@pytest.mark.parametrize('airlock_status',
                         [AirlockRequestStatus.Failed,
                          AirlockRequestStatus.Rejected,
                          AirlockRequestStatus.Blocked])
def test_validate_request_status_raises_error_for_unaccessible_request(airlock_status):
    airlock_request = sample_airlock_request(airlock_status)
    with pytest.raises(HTTPException) as ex:
        validate_request_status(airlock_request)

    assert ex.value.status_code == status.HTTP_400_BAD_REQUEST
    assert ex.value.detail == strings.AIRLOCK_REQUEST_UNACCESSIBLE


@pytest.mark.parametrize('airlock_status',
                         [AirlockRequestStatus.Submitted,
                          AirlockRequestStatus.InReview,
                          AirlockRequestStatus.ApprovalInProgress,
                          AirlockRequestStatus.Approved,
                          AirlockRequestStatus.RejectionInProgress,
                          AirlockRequestStatus.Rejected,
                          AirlockRequestStatus.Cancelled,
                          AirlockRequestStatus.BlockingInProgress,
                          AirlockRequestStatus.Blocked])
def test_get_required_permission_return_read_only_permissions_for_non_draft_requests(airlock_status):
    airlock_request = sample_airlock_request(airlock_status)
    permissions = get_required_permission(airlock_request)
    assert permissions.write is False
    assert permissions.delete is False
    assert permissions.read is True
    assert permissions.list is True


def test_get_required_permission_return_read_and_write_permissions_for_draft_requests():
    airlock_request = sample_airlock_request(AirlockRequestStatus.Draft)
    permissions = get_required_permission(airlock_request)
    assert permissions.write is True
    assert permissions.delete is True
    assert permissions.list is True
    assert permissions.read is True

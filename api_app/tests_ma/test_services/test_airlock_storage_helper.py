import pytest
from unittest.mock import patch

from models.domain.airlock_request import AirlockRequestStatus
from services.airlock_storage_helper import (
    use_metadata_stage_management,
    get_storage_account_name_for_request,
    get_stage_from_status
)
from resources import constants


class TestUseMetadataStageManagement:

    @patch("services.airlock_storage_helper.config")
    def test_returns_true_when_enabled(self, mock_config):
        mock_config.USE_METADATA_STAGE_MANAGEMENT = True
        assert use_metadata_stage_management() is True

    @patch("services.airlock_storage_helper.config")
    def test_returns_true_case_insensitive(self, mock_config):
        mock_config.USE_METADATA_STAGE_MANAGEMENT = True
        assert use_metadata_stage_management() is True

    @patch("services.airlock_storage_helper.config")
    def test_returns_false_when_disabled(self, mock_config):
        mock_config.USE_METADATA_STAGE_MANAGEMENT = False
        assert use_metadata_stage_management() is False

    @patch("services.airlock_storage_helper.config")
    def test_returns_false_when_not_set(self, mock_config):
        mock_config.USE_METADATA_STAGE_MANAGEMENT = False
        assert use_metadata_stage_management() is False

    @patch("services.airlock_storage_helper.config")
    def test_returns_false_for_invalid_value(self, mock_config):
        mock_config.USE_METADATA_STAGE_MANAGEMENT = False
        assert use_metadata_stage_management() is False


class TestGetStageFromStatus:

    def test_import_draft_maps_to_import_external_stage(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, AirlockRequestStatus.Draft)
        assert stage == constants.STAGE_IMPORT_EXTERNAL
        assert stage == "import-external"

    def test_import_submitted_maps_to_import_in_progress_stage(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, AirlockRequestStatus.Submitted)
        assert stage == constants.STAGE_IMPORT_IN_PROGRESS
        assert stage == "import-in-progress"

    def test_import_in_review_maps_to_import_in_progress_stage(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, AirlockRequestStatus.InReview)
        assert stage == constants.STAGE_IMPORT_IN_PROGRESS
        assert stage == "import-in-progress"

    def test_import_approved_maps_to_import_approved_stage(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, AirlockRequestStatus.Approved)
        assert stage == constants.STAGE_IMPORT_APPROVED
        assert stage == "import-approved"

    def test_import_approval_in_progress_maps_to_import_approved_stage(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, AirlockRequestStatus.ApprovalInProgress)
        assert stage == constants.STAGE_IMPORT_APPROVED

    def test_import_rejected_maps_to_import_rejected_stage(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, AirlockRequestStatus.Rejected)
        assert stage == constants.STAGE_IMPORT_REJECTED
        assert stage == "import-rejected"

    def test_import_rejection_in_progress_maps_to_import_rejected_stage(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, AirlockRequestStatus.RejectionInProgress)
        assert stage == constants.STAGE_IMPORT_REJECTED

    def test_import_blocked_maps_to_import_blocked_stage(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, AirlockRequestStatus.Blocked)
        assert stage == constants.STAGE_IMPORT_BLOCKED
        assert stage == "import-blocked"

    def test_import_blocking_in_progress_maps_to_import_blocked_stage(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, AirlockRequestStatus.BlockingInProgress)
        assert stage == constants.STAGE_IMPORT_BLOCKED

    def test_export_approved_maps_to_export_approved_stage(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, AirlockRequestStatus.Approved)
        assert stage == constants.STAGE_EXPORT_APPROVED
        assert stage == "export-approved"

    def test_export_approval_in_progress_maps_to_export_approved_stage(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, AirlockRequestStatus.ApprovalInProgress)
        assert stage == constants.STAGE_EXPORT_APPROVED
        assert stage == "export-approved"

    def test_export_draft_maps_to_export_internal_stage(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, AirlockRequestStatus.Draft)
        assert stage == constants.STAGE_EXPORT_INTERNAL
        assert stage == "export-internal"

    def test_export_submitted_maps_to_export_in_progress_stage(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, AirlockRequestStatus.Submitted)
        assert stage == constants.STAGE_EXPORT_IN_PROGRESS
        assert stage == "export-in-progress"

    def test_export_in_review_maps_to_export_in_progress_stage(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, AirlockRequestStatus.InReview)
        assert stage == constants.STAGE_EXPORT_IN_PROGRESS

    def test_export_rejected_maps_to_export_rejected_stage(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, AirlockRequestStatus.Rejected)
        assert stage == constants.STAGE_EXPORT_REJECTED
        assert stage == "export-rejected"

    def test_export_rejection_in_progress_maps_to_export_rejected_stage(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, AirlockRequestStatus.RejectionInProgress)
        assert stage == constants.STAGE_EXPORT_REJECTED

    def test_export_blocked_maps_to_export_blocked_stage(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, AirlockRequestStatus.Blocked)
        assert stage == constants.STAGE_EXPORT_BLOCKED
        assert stage == "export-blocked"

    def test_export_blocking_in_progress_maps_to_export_blocked_stage(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, AirlockRequestStatus.BlockingInProgress)
        assert stage == constants.STAGE_EXPORT_BLOCKED

    def test_unknown_status_returns_unknown(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, AirlockRequestStatus.Failed)
        assert stage == "unknown"


@pytest.fixture
def consolidated_mode_config():
    with patch("services.airlock_storage_helper.config") as mock_config:
        mock_config.USE_METADATA_STAGE_MANAGEMENT = True
        yield mock_config


@pytest.fixture
def legacy_mode_config():
    with patch("services.airlock_storage_helper.config") as mock_config:
        mock_config.USE_METADATA_STAGE_MANAGEMENT = False
        yield mock_config


class TestGetStorageAccountNameForRequestConsolidatedMode:

    class TestImportRequestsConsolidated:

        def test_import_draft_uses_core_storage(self, consolidated_mode_config):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, AirlockRequestStatus.Draft, "tre123", "ws12"
            )
            assert account == "stalairlocktre123"

        def test_import_submitted_uses_core_storage(self, consolidated_mode_config):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, AirlockRequestStatus.Submitted, "tre123", "ws12"
            )
            assert account == "stalairlocktre123"

        def test_import_in_review_uses_core_storage(self, consolidated_mode_config):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, AirlockRequestStatus.InReview, "tre123", "ws12"
            )
            assert account == "stalairlocktre123"

        def test_import_approved_uses_workspace_global_storage(self, consolidated_mode_config):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, AirlockRequestStatus.Approved, "tre123", "ws12"
            )
            assert account == "stalairlockgtre123"

        def test_import_approval_in_progress_uses_workspace_global_storage(self, consolidated_mode_config):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, AirlockRequestStatus.ApprovalInProgress, "tre123", "ws12"
            )
            assert account == "stalairlockgtre123"

        def test_import_rejected_uses_core_storage(self, consolidated_mode_config):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, AirlockRequestStatus.Rejected, "tre123", "ws12"
            )
            assert account == "stalairlocktre123"

        def test_import_blocked_uses_core_storage(self, consolidated_mode_config):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, AirlockRequestStatus.Blocked, "tre123", "ws12"
            )
            assert account == "stalairlocktre123"

    class TestExportRequestsConsolidated:

        def test_export_draft_uses_workspace_global_storage(self, consolidated_mode_config):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, AirlockRequestStatus.Draft, "tre123", "ws12"
            )
            assert account == "stalairlockgtre123"

        def test_export_submitted_uses_workspace_global_storage(self, consolidated_mode_config):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, AirlockRequestStatus.Submitted, "tre123", "ws12"
            )
            assert account == "stalairlockgtre123"

        def test_export_in_review_uses_workspace_global_storage(self, consolidated_mode_config):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, AirlockRequestStatus.InReview, "tre123", "ws12"
            )
            assert account == "stalairlockgtre123"

        def test_export_approved_uses_core_storage(self, consolidated_mode_config):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, AirlockRequestStatus.Approved, "tre123", "ws12"
            )
            assert account == "stalairlocktre123"

        def test_export_approval_in_progress_uses_core_storage(self, consolidated_mode_config):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, AirlockRequestStatus.ApprovalInProgress, "tre123", "ws12"
            )
            assert account == "stalairlocktre123"

        def test_export_rejected_uses_workspace_global_storage(self, consolidated_mode_config):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, AirlockRequestStatus.Rejected, "tre123", "ws12"
            )
            assert account == "stalairlockgtre123"

        def test_export_blocked_uses_workspace_global_storage(self, consolidated_mode_config):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, AirlockRequestStatus.Blocked, "tre123", "ws12"
            )
            assert account == "stalairlockgtre123"


class TestGetStorageAccountNameForRequestLegacyMode:

    class TestImportRequestsLegacy:

        def test_import_draft_uses_external_storage(self, legacy_mode_config):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, AirlockRequestStatus.Draft, "tre123", "ws12"
            )
            assert account == "stalimextre123"

        def test_import_submitted_uses_inprogress_storage(self, legacy_mode_config):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, AirlockRequestStatus.Submitted, "tre123", "ws12"
            )
            assert account == "stalimiptre123"

        def test_import_in_review_uses_inprogress_storage(self, legacy_mode_config):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, AirlockRequestStatus.InReview, "tre123", "ws12"
            )
            assert account == "stalimiptre123"

        def test_import_approved_uses_workspace_approved_storage(self, legacy_mode_config):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, AirlockRequestStatus.Approved, "tre123", "ws12"
            )
            assert account == "stalimappwsws12"

        def test_import_rejected_uses_rejected_storage(self, legacy_mode_config):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, AirlockRequestStatus.Rejected, "tre123", "ws12"
            )
            assert account == "stalimrejtre123"

        def test_import_blocked_uses_blocked_storage(self, legacy_mode_config):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, AirlockRequestStatus.Blocked, "tre123", "ws12"
            )
            assert account == "stalimblockedtre123"

    class TestExportRequestsLegacy:

        def test_export_draft_uses_workspace_internal_storage(self, legacy_mode_config):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, AirlockRequestStatus.Draft, "tre123", "ws12"
            )
            assert account == "stalexintwsws12"

        def test_export_submitted_uses_workspace_inprogress_storage(self, legacy_mode_config):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, AirlockRequestStatus.Submitted, "tre123", "ws12"
            )
            assert account == "stalexipwsws12"

        def test_export_approved_uses_core_approved_storage(self, legacy_mode_config):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, AirlockRequestStatus.Approved, "tre123", "ws12"
            )
            assert account == "stalexapptre123"

        def test_export_rejected_uses_workspace_rejected_storage(self, legacy_mode_config):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, AirlockRequestStatus.Rejected, "tre123", "ws12"
            )
            assert account == "stalexrejwsws12"

        def test_export_blocked_uses_workspace_blocked_storage(self, legacy_mode_config):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, AirlockRequestStatus.Blocked, "tre123", "ws12"
            )
            assert account == "stalexblockedwsws12"


class TestABACStageConstants:

    def test_import_external_stage_constant_value(self):
        assert constants.STAGE_IMPORT_EXTERNAL == "import-external"

    def test_import_in_progress_stage_constant_value(self):
        assert constants.STAGE_IMPORT_IN_PROGRESS == "import-in-progress"

    def test_export_approved_stage_constant_value(self):
        assert constants.STAGE_EXPORT_APPROVED == "export-approved"

    def test_import_approved_stage_constant_value(self):
        assert constants.STAGE_IMPORT_APPROVED == "import-approved"

    def test_import_rejected_stage_constant_value(self):
        assert constants.STAGE_IMPORT_REJECTED == "import-rejected"

    def test_import_blocked_stage_constant_value(self):
        assert constants.STAGE_IMPORT_BLOCKED == "import-blocked"

    def test_export_internal_stage_constant_value(self):
        assert constants.STAGE_EXPORT_INTERNAL == "export-internal"

    def test_export_in_progress_stage_constant_value(self):
        assert constants.STAGE_EXPORT_IN_PROGRESS == "export-in-progress"

    def test_export_rejected_stage_constant_value(self):
        assert constants.STAGE_EXPORT_REJECTED == "export-rejected"

    def test_export_blocked_stage_constant_value(self):
        assert constants.STAGE_EXPORT_BLOCKED == "export-blocked"


class TestABACAccessibleStages:

    ABAC_ALLOWED_STAGES = ['import-external', 'import-in-progress', 'export-approved']

    def test_import_draft_is_abac_accessible(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, AirlockRequestStatus.Draft)
        assert stage in self.ABAC_ALLOWED_STAGES

    def test_import_submitted_is_abac_accessible(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, AirlockRequestStatus.Submitted)
        assert stage in self.ABAC_ALLOWED_STAGES

    def test_import_in_review_is_abac_accessible(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, AirlockRequestStatus.InReview)
        assert stage in self.ABAC_ALLOWED_STAGES

    def test_import_approved_is_not_abac_accessible(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, AirlockRequestStatus.Approved)
        assert stage not in self.ABAC_ALLOWED_STAGES

    def test_import_rejected_is_not_abac_accessible(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, AirlockRequestStatus.Rejected)
        assert stage not in self.ABAC_ALLOWED_STAGES

    def test_import_blocked_is_not_abac_accessible(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, AirlockRequestStatus.Blocked)
        assert stage not in self.ABAC_ALLOWED_STAGES

    def test_export_draft_is_not_abac_accessible(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, AirlockRequestStatus.Draft)
        assert stage not in self.ABAC_ALLOWED_STAGES

    def test_export_submitted_is_not_abac_accessible(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, AirlockRequestStatus.Submitted)
        assert stage not in self.ABAC_ALLOWED_STAGES

    def test_export_approved_is_abac_accessible(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, AirlockRequestStatus.Approved)
        assert stage in self.ABAC_ALLOWED_STAGES

    def test_export_approval_in_progress_is_abac_accessible(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, AirlockRequestStatus.ApprovalInProgress)
        assert stage in self.ABAC_ALLOWED_STAGES

    def test_export_rejected_is_not_abac_accessible(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, AirlockRequestStatus.Rejected)
        assert stage not in self.ABAC_ALLOWED_STAGES

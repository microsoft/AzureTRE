import os
import pytest
from unittest.mock import patch

from shared_code.airlock_storage_helper import (
    use_metadata_stage_management,
    get_storage_account_name_for_request,
    get_stage_from_status
)
from shared_code import constants


class TestUseMetadataStageManagement:

    @patch.dict(os.environ, {"USE_METADATA_STAGE_MANAGEMENT": "true"}, clear=True)
    def test_returns_true_when_enabled(self):
        assert use_metadata_stage_management() is True

    @patch.dict(os.environ, {"USE_METADATA_STAGE_MANAGEMENT": "TRUE"}, clear=True)
    def test_returns_true_case_insensitive(self):
        assert use_metadata_stage_management() is True

    @patch.dict(os.environ, {"USE_METADATA_STAGE_MANAGEMENT": "false"}, clear=True)
    def test_returns_false_when_disabled(self):
        assert use_metadata_stage_management() is False

    @patch.dict(os.environ, {}, clear=True)
    def test_returns_false_when_not_set(self):
        assert use_metadata_stage_management() is False


class TestGetStageFromStatus:

    def test_import_draft_maps_to_import_external(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, constants.STAGE_DRAFT)
        assert stage == constants.STAGE_IMPORT_EXTERNAL

    def test_import_submitted_maps_to_import_in_progress(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, constants.STAGE_SUBMITTED)
        assert stage == constants.STAGE_IMPORT_IN_PROGRESS

    def test_import_in_review_maps_to_import_in_progress(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, constants.STAGE_IN_REVIEW)
        assert stage == constants.STAGE_IMPORT_IN_PROGRESS

    def test_import_approved_maps_to_import_approved(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, constants.STAGE_APPROVED)
        assert stage == constants.STAGE_IMPORT_APPROVED

    def test_import_approval_in_progress_maps_to_import_approved(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, constants.STAGE_APPROVAL_INPROGRESS)
        assert stage == constants.STAGE_IMPORT_APPROVED

    def test_import_rejected_maps_to_import_rejected(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, constants.STAGE_REJECTED)
        assert stage == constants.STAGE_IMPORT_REJECTED

    def test_import_rejection_in_progress_maps_to_import_rejected(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, constants.STAGE_REJECTION_INPROGRESS)
        assert stage == constants.STAGE_IMPORT_REJECTED

    def test_import_blocked_maps_to_import_blocked(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, constants.STAGE_BLOCKED_BY_SCAN)
        assert stage == constants.STAGE_IMPORT_BLOCKED

    def test_import_blocking_in_progress_maps_to_import_blocked(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, constants.STAGE_BLOCKING_INPROGRESS)
        assert stage == constants.STAGE_IMPORT_BLOCKED

    def test_export_draft_maps_to_export_internal(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, constants.STAGE_DRAFT)
        assert stage == constants.STAGE_EXPORT_INTERNAL

    def test_export_submitted_maps_to_export_in_progress(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, constants.STAGE_SUBMITTED)
        assert stage == constants.STAGE_EXPORT_IN_PROGRESS

    def test_export_in_review_maps_to_export_in_progress(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, constants.STAGE_IN_REVIEW)
        assert stage == constants.STAGE_EXPORT_IN_PROGRESS

    def test_export_approved_maps_to_export_approved(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, constants.STAGE_APPROVED)
        assert stage == constants.STAGE_EXPORT_APPROVED

    def test_export_approval_in_progress_maps_to_export_approved(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, constants.STAGE_APPROVAL_INPROGRESS)
        assert stage == constants.STAGE_EXPORT_APPROVED

    def test_export_rejected_maps_to_export_rejected(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, constants.STAGE_REJECTED)
        assert stage == constants.STAGE_EXPORT_REJECTED

    def test_export_rejection_in_progress_maps_to_export_rejected(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, constants.STAGE_REJECTION_INPROGRESS)
        assert stage == constants.STAGE_EXPORT_REJECTED

    def test_export_blocked_maps_to_export_blocked(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, constants.STAGE_BLOCKED_BY_SCAN)
        assert stage == constants.STAGE_EXPORT_BLOCKED

    def test_export_blocking_in_progress_maps_to_export_blocked(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, constants.STAGE_BLOCKING_INPROGRESS)
        assert stage == constants.STAGE_EXPORT_BLOCKED

    def test_unknown_status_returns_unknown(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, "nonexistent_status")
        assert stage == "unknown"


class TestGetStorageAccountNameForRequestConsolidated:

    @patch.dict(os.environ, {"USE_METADATA_STAGE_MANAGEMENT": "true", "TRE_ID": "tre123"}, clear=True)
    class TestImportRequests:

        def test_import_draft_uses_core_storage(self):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, constants.STAGE_DRAFT, "ws12"
            )
            assert account == "stalairlocktre123"

        def test_import_submitted_uses_core_storage(self):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, constants.STAGE_SUBMITTED, "ws12"
            )
            assert account == "stalairlocktre123"

        def test_import_in_review_uses_core_storage(self):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, constants.STAGE_IN_REVIEW, "ws12"
            )
            assert account == "stalairlocktre123"

        def test_import_approved_uses_workspace_global_storage(self):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, constants.STAGE_APPROVED, "ws12"
            )
            assert account == "stalairlockgtre123"

        def test_import_approval_in_progress_uses_workspace_global_storage(self):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, constants.STAGE_APPROVAL_INPROGRESS, "ws12"
            )
            assert account == "stalairlockgtre123"

        def test_import_rejected_uses_core_storage(self):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, constants.STAGE_REJECTED, "ws12"
            )
            assert account == "stalairlocktre123"

        def test_import_rejection_in_progress_uses_core_storage(self):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, constants.STAGE_REJECTION_INPROGRESS, "ws12"
            )
            assert account == "stalairlocktre123"

        def test_import_blocked_uses_core_storage(self):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, constants.STAGE_BLOCKED_BY_SCAN, "ws12"
            )
            assert account == "stalairlocktre123"

        def test_import_blocking_in_progress_uses_core_storage(self):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, constants.STAGE_BLOCKING_INPROGRESS, "ws12"
            )
            assert account == "stalairlocktre123"

    @patch.dict(os.environ, {"USE_METADATA_STAGE_MANAGEMENT": "true", "TRE_ID": "tre123"}, clear=True)
    class TestExportRequests:

        def test_export_draft_uses_workspace_global_storage(self):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, constants.STAGE_DRAFT, "ws12"
            )
            assert account == "stalairlockgtre123"

        def test_export_submitted_uses_workspace_global_storage(self):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, constants.STAGE_SUBMITTED, "ws12"
            )
            assert account == "stalairlockgtre123"

        def test_export_approved_uses_core_storage(self):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, constants.STAGE_APPROVED, "ws12"
            )
            assert account == "stalairlocktre123"

        def test_export_approval_in_progress_uses_core_storage(self):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, constants.STAGE_APPROVAL_INPROGRESS, "ws12"
            )
            assert account == "stalairlocktre123"

        def test_export_rejected_uses_workspace_global_storage(self):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, constants.STAGE_REJECTED, "ws12"
            )
            assert account == "stalairlockgtre123"

        def test_export_blocked_uses_workspace_global_storage(self):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, constants.STAGE_BLOCKED_BY_SCAN, "ws12"
            )
            assert account == "stalairlockgtre123"


class TestGetStorageAccountNameForRequestLegacy:

    @patch.dict(os.environ, {"USE_METADATA_STAGE_MANAGEMENT": "false", "TRE_ID": "tre123"}, clear=True)
    class TestImportRequestsLegacy:

        def test_import_draft_uses_external_storage(self):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, constants.STAGE_DRAFT, "ws12"
            )
            assert account == "stalimextre123"

        def test_import_submitted_uses_inprogress_storage(self):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, constants.STAGE_SUBMITTED, "ws12"
            )
            assert account == "stalimiptre123"

        def test_import_approved_uses_workspace_storage(self):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, constants.STAGE_APPROVED, "ws12"
            )
            assert account == "stalimappwsws12"

        def test_import_rejected_uses_rejected_storage(self):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, constants.STAGE_REJECTED, "ws12"
            )
            assert account == "stalimrejtre123"

        def test_import_blocked_uses_blocked_storage(self):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, constants.STAGE_BLOCKED_BY_SCAN, "ws12"
            )
            assert account == "stalimblockedtre123"

    @patch.dict(os.environ, {"USE_METADATA_STAGE_MANAGEMENT": "false", "TRE_ID": "tre123"}, clear=True)
    class TestExportRequestsLegacy:

        def test_export_draft_uses_internal_storage(self):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, constants.STAGE_DRAFT, "ws12"
            )
            assert account == "stalexintwsws12"

        def test_export_submitted_uses_inprogress_storage(self):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, constants.STAGE_SUBMITTED, "ws12"
            )
            assert account == "stalexipwsws12"

        def test_export_approved_uses_approved_storage(self):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, constants.STAGE_APPROVED, "ws12"
            )
            assert account == "stalexapptre123"

        def test_export_rejected_uses_rejected_storage(self):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, constants.STAGE_REJECTED, "ws12"
            )
            assert account == "stalexrejwsws12"

        def test_export_blocked_uses_blocked_storage(self):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, constants.STAGE_BLOCKED_BY_SCAN, "ws12"
            )
            assert account == "stalexblockedwsws12"


class TestABACStageConstants:

    def test_stage_import_external_value(self):
        assert constants.STAGE_IMPORT_EXTERNAL == "import-external"

    def test_stage_import_in_progress_value(self):
        assert constants.STAGE_IMPORT_IN_PROGRESS == "import-in-progress"

    def test_stage_import_approved_value(self):
        assert constants.STAGE_IMPORT_APPROVED == "import-approved"

    def test_stage_import_rejected_value(self):
        assert constants.STAGE_IMPORT_REJECTED == "import-rejected"

    def test_stage_import_blocked_value(self):
        assert constants.STAGE_IMPORT_BLOCKED == "import-blocked"

    def test_stage_export_internal_value(self):
        assert constants.STAGE_EXPORT_INTERNAL == "export-internal"

    def test_stage_export_in_progress_value(self):
        assert constants.STAGE_EXPORT_IN_PROGRESS == "export-in-progress"

    def test_stage_export_approved_value(self):
        assert constants.STAGE_EXPORT_APPROVED == "export-approved"

    def test_stage_export_rejected_value(self):
        assert constants.STAGE_EXPORT_REJECTED == "export-rejected"

    def test_stage_export_blocked_value(self):
        assert constants.STAGE_EXPORT_BLOCKED == "export-blocked"


class TestABACAccessPatterns:

    ABAC_ALLOWED_STAGES = ['import-external', 'import-in-progress', 'export-approved']

    def test_import_draft_is_api_accessible(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, constants.STAGE_DRAFT)
        assert stage in self.ABAC_ALLOWED_STAGES

    def test_import_submitted_is_api_accessible(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, constants.STAGE_SUBMITTED)
        assert stage in self.ABAC_ALLOWED_STAGES

    def test_import_in_review_is_api_accessible(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, constants.STAGE_IN_REVIEW)
        assert stage in self.ABAC_ALLOWED_STAGES

    def test_import_approved_is_not_api_accessible(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, constants.STAGE_APPROVED)
        assert stage not in self.ABAC_ALLOWED_STAGES

    def test_import_rejected_is_not_api_accessible(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, constants.STAGE_REJECTED)
        assert stage not in self.ABAC_ALLOWED_STAGES

    def test_import_blocked_is_not_api_accessible(self):
        stage = get_stage_from_status(constants.IMPORT_TYPE, constants.STAGE_BLOCKED_BY_SCAN)
        assert stage not in self.ABAC_ALLOWED_STAGES

    def test_export_draft_is_not_api_accessible(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, constants.STAGE_DRAFT)
        assert stage not in self.ABAC_ALLOWED_STAGES

    def test_export_submitted_is_not_api_accessible(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, constants.STAGE_SUBMITTED)
        assert stage not in self.ABAC_ALLOWED_STAGES

    def test_export_approved_is_api_accessible(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, constants.STAGE_APPROVED)
        assert stage in self.ABAC_ALLOWED_STAGES

    def test_export_rejected_is_not_api_accessible(self):
        stage = get_stage_from_status(constants.EXPORT_TYPE, constants.STAGE_REJECTED)
        assert stage not in self.ABAC_ALLOWED_STAGES

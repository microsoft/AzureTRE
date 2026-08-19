from models.domain.airlock_request import AirlockRequestStatus
from services.airlock_storage_helper import get_storage_account_name_for_request
from resources import constants


class TestGetStorageAccountNameForRequestConsolidatedMode:

    class TestImportRequestsConsolidated:

        def test_import_draft_uses_core_storage(self):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, AirlockRequestStatus.Draft, "tre123"
            )
            assert account == "stalairlocktre123"

        def test_import_submitted_uses_core_storage(self):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, AirlockRequestStatus.Submitted, "tre123"
            )
            assert account == "stalairlocktre123"

        def test_import_in_review_uses_core_storage(self):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, AirlockRequestStatus.InReview, "tre123"
            )
            assert account == "stalairlocktre123"

        def test_import_approved_uses_workspace_global_storage(self):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, AirlockRequestStatus.Approved, "tre123"
            )
            assert account == "stalairlockgtre123"

        def test_import_approval_in_progress_uses_workspace_global_storage(self):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, AirlockRequestStatus.ApprovalInProgress, "tre123"
            )
            assert account == "stalairlockgtre123"

        def test_import_rejected_uses_core_storage(self):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, AirlockRequestStatus.Rejected, "tre123"
            )
            assert account == "stalairlocktre123"

        def test_import_blocked_uses_core_storage(self):
            account = get_storage_account_name_for_request(
                constants.IMPORT_TYPE, AirlockRequestStatus.Blocked, "tre123"
            )
            assert account == "stalairlocktre123"

    class TestExportRequestsConsolidated:

        def test_export_draft_uses_workspace_global_storage(self):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, AirlockRequestStatus.Draft, "tre123"
            )
            assert account == "stalairlockgtre123"

        def test_export_submitted_uses_workspace_global_storage(self):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, AirlockRequestStatus.Submitted, "tre123"
            )
            assert account == "stalairlockgtre123"

        def test_export_in_review_uses_workspace_global_storage(self):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, AirlockRequestStatus.InReview, "tre123"
            )
            assert account == "stalairlockgtre123"

        def test_export_approved_uses_core_storage(self):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, AirlockRequestStatus.Approved, "tre123"
            )
            assert account == "stalairlocktre123"

        def test_export_approval_in_progress_uses_core_storage(self):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, AirlockRequestStatus.ApprovalInProgress, "tre123"
            )
            assert account == "stalairlocktre123"

        def test_export_rejected_uses_workspace_global_storage(self):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, AirlockRequestStatus.Rejected, "tre123"
            )
            assert account == "stalairlockgtre123"

        def test_export_blocked_uses_workspace_global_storage(self):
            account = get_storage_account_name_for_request(
                constants.EXPORT_TYPE, AirlockRequestStatus.Blocked, "tre123"
            )
            assert account == "stalairlockgtre123"


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

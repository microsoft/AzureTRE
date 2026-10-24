"""Check the order and the checks of the Airlock v1 to v2 move without Azure."""

import base64
import json
import os
import unittest
from unittest.mock import AsyncMock, Mock, patch

from e2e_tests import test_airlock_migration as migration
from e2e_tests.token_provider import TokenProvider

WORKSPACE = "11111111-1111-4111-8111-111111111111"
PATH = f"/workspaces/{WORKSPACE}"


def token(roles):
    # get_workspace_owner_token returns a TokenProvider, not the token text.
    payload = base64.urlsafe_b64encode(json.dumps({"roles": roles}).encode()).decode().rstrip("=")
    credential = Mock()
    credential.get_token.return_value.token = "header." + payload + ".signature"
    return TokenProvider(credential, "api://workspace/.default")


class MigrationFlowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.events = []
        self.version = 1
        self.patch_codes = {2: 400, 1: 400}
        self.enterContext(
            patch.dict(os.environ, AZURE_ENVIRONMENT="AzureCloud", AIRLOCK_MIGRATION_VALIDATION_DEADLINE="")
        )
        for name, value in (
            ("TRE_ID", "tre-test"),
            ("TEST_WORKSPACE_APP_ID", "app"),
            ("TEST_WORKSPACE_APP_SECRET", "s"),
        ):
            self.enterContext(patch.object(migration.config, name, value))
        create = AsyncMock(return_value=(PATH, WORKSPACE))
        self.create = self.enterContext(patch.object(migration, "create_or_get_test_workspace", create))
        self.enterContext(
            patch.object(
                migration,
                "clean_up_test_workspace",
                AsyncMock(side_effect=lambda *a: self.events.append("delete-workspace")),
            )
        )
        owner = token(["WorkspaceOwner", "AirlockManager"])
        self.enterContext(patch.object(migration, "get_workspace_owner_token", AsyncMock(return_value=owner)))
        self.enterContext(patch.object(migration, "get_admin_token", AsyncMock(return_value="admin")))

        async def resource(endpoint, *args):
            return {"workspace": {"_etag": "etag", "properties": {"airlock_version": self.version}}}

        self.enterContext(patch.object(migration, "get_resource", resource))

        async def submit(*args):
            self.events.append("legacy-import")
            return "legacy", "https://stalimextretest.blob.core.windows.net/legacy?sig=x"

        async def draft(*args):
            account = "stalimextretest" if self.version == 1 else "stalairlocktretest"
            name = f"draft-v{self.version}"
            self.events.append(name)
            suffix = "-draft" if self.version == 2 else ""
            return name, f"https://{account}.blob.core.windows.net/{name}{suffix}?sig=x"

        self.enterContext(patch.object(migration, "submit_airlock_import_request", submit))
        self.enterContext(patch.object(migration, "create_draft_import_request_with_file", draft))

        async def post(payload, endpoint, *args):
            self.events.append(endpoint.rsplit("/", 1)[-1])
            return {"migrations": []}

        self.enterContext(patch.object(migration, "post_request", post))
        self.enterContext(
            patch.object(
                migration, "wait_for_status", AsyncMock(side_effect=lambda state, *a: self.events.append(state))
            )
        )

        async def request(endpoint, *args):
            request_id = endpoint.rsplit("/", 1)[-1]
            version = 1 if request_id == "legacy" else 2
            return {"airlockRequest": {"status": "approved", "airlock_version": version}}

        self.enterContext(patch.object(migration, "get_request", request))

        async def patch_status(path, properties, *args):
            self.events.append(f"patch-v{properties['airlock_version']}")
            return self.patch_codes[properties["airlock_version"]]

        self.enterContext(patch.object(migration, "patch_status", patch_status))

        async def move(payload, *args, **kwargs):
            self.events.append("move-to-v2")
            self.version = 2

        self.enterContext(patch.object(migration, "post_resource", move))

    async def test_the_move_follows_the_documented_steps(self):
        await migration.test_legacy_airlock_workspace_moves_to_v2(True)
        self.assertEqual(
            self.events,
            [
                "legacy-import",
                "review",
                "approved",
                "migrations",
                "migrations",
                "draft-v1",
                "patch-v2",
                "cancel",
                "move-to-v2",
                "draft-v2",
                "cancel",
                "patch-v1",
                "delete-workspace",
            ],
        )
        self.assertEqual(self.create.await_args.kwargs["properties"], {"enable_airlock": True, "airlock_version": 1})
        self.assertEqual(self.create.await_args.kwargs["auth_type"], "Manual")

    async def test_a_move_with_a_request_in_progress_must_be_refused(self):
        self.patch_codes[2] = 202
        with self.assertRaises(AssertionError):
            await migration.test_legacy_airlock_workspace_moves_to_v2(True)
        self.assertNotIn("move-to-v2", self.events)
        self.assertEqual(self.events[-1], "delete-workspace")

    async def test_a_missing_review_role_fails_before_any_request(self):
        self.enterContext(
            patch.object(migration, "get_workspace_owner_token", AsyncMock(return_value=token(["WorkspaceOwner"])))
        )
        with self.assertRaisesRegex(ValueError, "AirlockManager"):
            await migration.test_legacy_airlock_workspace_moves_to_v2(True)
        self.assertEqual(self.events, ["delete-workspace"])

    def test_the_storage_account_comes_from_the_host(self):
        self.assertEqual(migration.storage_account("https://stalimextre.blob.core.windows.net/x?sig=y"), "stalimextre")

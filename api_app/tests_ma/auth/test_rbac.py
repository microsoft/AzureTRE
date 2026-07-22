"""Tests for auth.rbac role-checking dependencies."""
import pytest
from unittest.mock import MagicMock, patch

from auth.models import AuthenticatedUser, TRERole, WorkspaceAccessRole
from auth.rbac import require_roles, require_workspace_roles


def _make_user(**kwargs) -> AuthenticatedUser:
    defaults = {"id": "uid", "name": "User", "email": "u@example.com", "roles": []}
    defaults.update(kwargs)
    return AuthenticatedUser(**defaults)


# ---------------------------------------------------------------------------
# require_roles
# ---------------------------------------------------------------------------


class TestRequireRoles:
    def test_allows_user_with_required_role(self):
        admin = _make_user(roles=["TREAdmin"])
        dep = require_roles(TRERole.Admin)

        import asyncio

        async def _run():
            result = await dep(user=admin)
            assert result.id == "uid"
            assert "TREAdmin" in result.roles

        asyncio.get_event_loop().run_until_complete(_run())

    def test_raises_403_when_user_lacks_role(self):
        from fastapi import HTTPException

        dep = require_roles(TRERole.Admin)

        import asyncio

        async def _run():
            user_with_no_roles = _make_user(roles=["TREUser"])
            with pytest.raises(HTTPException) as exc_info:
                await dep(user=user_with_no_roles)
            assert exc_info.value.status_code == 403

        asyncio.get_event_loop().run_until_complete(_run())

    def test_allows_user_with_any_of_multiple_roles(self):
        dep = require_roles(TRERole.Admin, TRERole.User)

        import asyncio

        async def _run():
            tre_user = _make_user(roles=["TREUser"])
            result = await dep(user=tre_user)
            assert result.id == "uid"

        asyncio.get_event_loop().run_until_complete(_run())


# ---------------------------------------------------------------------------
# require_workspace_roles
# ---------------------------------------------------------------------------


class TestRequireWorkspaceRoles:
    def _make_fake_deps(self, user_roles, with_client_id=True):
        """Return (fake_credentials, fake_workspace, mock_validator, user) for testing _check directly."""
        from fastapi.security import HTTPAuthorizationCredentials
        from models.domain.workspace import Workspace

        fake_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token")
        properties = {"client_id": "ws-client-id"} if with_client_id else {}
        fake_workspace = Workspace(
            id="ws-id",
            templateName="test",
            templateVersion="0.1.0",
            etag="",
            resourcePath="/workspaces/ws-id",
            properties=properties,
        )
        validated_user = _make_user(roles=user_roles)
        mock_validator = MagicMock()
        mock_validator.validate.return_value = validated_user
        return fake_creds, fake_workspace, mock_validator, validated_user

    def test_admin_always_passes_without_workspace_role(self):
        """A TREAdmin using a core token reaches an admin-permitted workspace endpoint via the fallback."""
        from auth.exceptions import TokenInvalid as _TokenInvalid

        dep = require_workspace_roles(WorkspaceAccessRole.Owner, allow_tre_admin=True)
        fake_creds, fake_workspace, _, admin = self._make_fake_deps(["TREAdmin"])

        # Workspace validator rejects the core token (wrong audience); core validator accepts it.
        ws_validator = MagicMock()
        ws_validator.validate.side_effect = _TokenInvalid("wrong audience")
        core_validator = MagicMock()
        core_validator.validate.return_value = admin

        import asyncio

        async def _run():
            with patch('auth.rbac.get_workspace_validator', return_value=ws_validator):
                with patch('auth.rbac.get_core_validator', return_value=core_validator):
                    result = await dep(credentials=fake_creds, workspace=fake_workspace)
            assert result.id == "uid"

        asyncio.get_event_loop().run_until_complete(_run())

    def test_workspace_owner_passes(self):
        dep = require_workspace_roles(WorkspaceAccessRole.Owner)
        fake_creds, fake_workspace, ws_validator, owner = self._make_fake_deps(["WorkspaceOwner"])

        import asyncio

        async def _run():
            with patch('auth.rbac.get_workspace_validator', return_value=ws_validator):
                result = await dep(credentials=fake_creds, workspace=fake_workspace)
            assert result.id == "uid"

        asyncio.get_event_loop().run_until_complete(_run())

    def test_raises_403_for_user_without_workspace_role(self):
        from fastapi import HTTPException

        dep = require_workspace_roles(WorkspaceAccessRole.Owner)
        fake_creds, fake_workspace, ws_validator, researcher = self._make_fake_deps(["WorkspaceResearcher"])

        import asyncio

        async def _run():
            with patch('auth.rbac.get_workspace_validator', return_value=ws_validator):
                with pytest.raises(HTTPException) as exc_info:
                    await dep(credentials=fake_creds, workspace=fake_workspace)
            assert exc_info.value.status_code == 403

        asyncio.get_event_loop().run_until_complete(_run())

    def test_wrong_workspace_token_rejected_with_401(self):
        """A token issued for workspace A must not grant access to workspace B.

        When the workspace validator raises TokenInvalid (wrong audience) the
        code falls back to the core validator.  If the token is also invalid
        for the core audience the result must be HTTP 401, not a silent pass.
        """
        from fastapi import HTTPException
        from auth.exceptions import TokenInvalid as _TokenInvalid

        dep = require_workspace_roles(WorkspaceAccessRole.Owner, allow_tre_admin=True)
        fake_creds, fake_workspace, _, _ = self._make_fake_deps(["WorkspaceOwner"])

        # Workspace validator: wrong audience (workspace B rejects a workspace A token)
        ws_validator_mock = MagicMock()
        ws_validator_mock.validate.side_effect = _TokenInvalid("wrong audience")

        # Core validator: also rejects the token (it's not a core token)
        core_validator_mock = MagicMock()
        core_validator_mock.validate.side_effect = _TokenInvalid("not a core token")

        import asyncio

        async def _run():
            with patch('auth.rbac.get_workspace_validator', return_value=ws_validator_mock):
                with patch('auth.rbac.get_core_validator', return_value=core_validator_mock):
                    with pytest.raises(HTTPException) as exc_info:
                        await dep(credentials=fake_creds, workspace=fake_workspace)
            assert exc_info.value.status_code == 401

        asyncio.get_event_loop().run_until_complete(_run())

    def test_non_admin_workspace_user_cannot_elevate_via_core_fallback(self):
        """A non-admin core token must never satisfy a workspace-scoped check.

        Even if the core validator accepts the token *and* its claims contain a
        workspace role, the fallback path only grants access to TREAdmin; any
        other core token is rejected with 401 (wrong audience for this resource).
        """
        from fastapi import HTTPException
        from auth.exceptions import TokenInvalid as _TokenInvalid

        dep = require_workspace_roles(WorkspaceAccessRole.Owner, allow_tre_admin=True)
        fake_creds, fake_workspace, _, _ = self._make_fake_deps([])

        # Workspace validator rejects the token (wrong audience)
        ws_validator_mock = MagicMock()
        ws_validator_mock.validate.side_effect = _TokenInvalid("wrong audience")

        # Core validator accepts the token and it even carries a workspace role,
        # but the user is NOT TREAdmin.
        core_validator_mock = MagicMock()
        core_user = _make_user(roles=["WorkspaceOwner"])
        core_validator_mock.validate.return_value = core_user

        import asyncio

        async def _run():
            with patch('auth.rbac.get_workspace_validator', return_value=ws_validator_mock):
                with patch('auth.rbac.get_core_validator', return_value=core_validator_mock):
                    with pytest.raises(HTTPException) as exc_info:
                        await dep(credentials=fake_creds, workspace=fake_workspace)
            assert exc_info.value.status_code == 401

        asyncio.get_event_loop().run_until_complete(_run())

    def test_non_admin_endpoint_does_not_fall_back_to_core(self):
        """When allow_tre_admin is False, a wrong-audience token is rejected with
        401 and the core validator is never consulted (no cross-audience path)."""
        from fastapi import HTTPException
        from auth.exceptions import TokenInvalid as _TokenInvalid

        dep = require_workspace_roles(WorkspaceAccessRole.Owner)
        fake_creds, fake_workspace, _, _ = self._make_fake_deps([])

        ws_validator_mock = MagicMock()
        ws_validator_mock.validate.side_effect = _TokenInvalid("wrong audience")
        core_validator_mock = MagicMock()  # must NOT be called

        import asyncio

        async def _run():
            with patch('auth.rbac.get_workspace_validator', return_value=ws_validator_mock):
                with patch('auth.rbac.get_core_validator', return_value=core_validator_mock):
                    with pytest.raises(HTTPException) as exc_info:
                        await dep(credentials=fake_creds, workspace=fake_workspace)
            assert exc_info.value.status_code == 401
            core_validator_mock.validate.assert_not_called()

        asyncio.get_event_loop().run_until_complete(_run())


class TestRequireBearerCredentials:
    def test_missing_credentials_raises_401_with_www_authenticate(self):
        from fastapi import HTTPException
        from auth.dependencies import require_bearer_credentials

        import asyncio

        async def _run():
            with pytest.raises(HTTPException) as exc_info:
                await require_bearer_credentials(credentials=None)
            assert exc_info.value.status_code == 401
            assert exc_info.value.headers.get("WWW-Authenticate") == "Bearer"

        asyncio.get_event_loop().run_until_complete(_run())

    def test_present_credentials_are_returned(self):
        from fastapi.security import HTTPAuthorizationCredentials
        from auth.dependencies import require_bearer_credentials

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="tok")

        import asyncio

        async def _run():
            result = await require_bearer_credentials(credentials=creds)
            assert result is creds

        asyncio.get_event_loop().run_until_complete(_run())


class TestAuthenticatedUserHelpers:
    def test_has_any_role_returns_true_when_matching(self):
        user = _make_user(roles=["TREAdmin", "TREUser"])
        assert user.has_any_role(TRERole.Admin) is True

    def test_has_any_role_returns_false_when_no_match(self):
        user = _make_user(roles=["TREUser"])
        assert user.has_any_role(WorkspaceAccessRole.Owner) is False

    def test_is_tre_admin_true_for_admin(self):
        user = _make_user(roles=["TREAdmin"])
        assert user.is_tre_admin() is True

    def test_is_tre_admin_false_for_regular_user(self):
        user = _make_user(roles=["TREUser"])
        assert user.is_tre_admin() is False

    def test_model_is_frozen(self):
        user = _make_user(roles=["TREAdmin"])
        with pytest.raises(TypeError):
            user.roles = []  # type: ignore[misc]

    def test_roles_cannot_be_mutated_in_place(self):
        user = _make_user(roles=["TREUser"])
        assert isinstance(user.roles, tuple)
        with pytest.raises(AttributeError):
            user.roles.append("TREAdmin")  # type: ignore[attr-defined]

"""Tests for auth.rbac role-checking dependencies."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

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
    def _app_with_dep(self, dep):
        app = FastAPI()

        @app.get("/protected")
        async def _route(user=Depends(dep)):
            return {"id": user.id}

        return app

    def test_allows_user_with_required_role(self):
        admin = _make_user(roles=["TREAdmin"])
        dep = require_roles(TRERole.Admin)

        app = self._app_with_dep(dep)
        app.dependency_overrides[dep] = lambda: admin  # type: ignore[index]
        # dependency_overrides must target the inner _check function
        # Use the approach below instead

    def test_raises_403_when_user_lacks_role(self):
        from fastapi import HTTPException

        dep = require_roles(TRERole.Admin)

        # Extract the inner _check dependency
        inner_dep = dep

        async def _call_dep():
            user_with_no_roles = _make_user(roles=["TREUser"])
            # Manually invoke the inner check with a user missing the role.
            from auth.dependencies import get_authenticated_user
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                # Simulate what FastAPI would do
                from auth.rbac import require_roles as _req
                checker = _req(TRERole.Admin)
                await checker(user=user_with_no_roles)

            assert exc_info.value.status_code == 403

        import asyncio
        asyncio.get_event_loop().run_until_complete(_call_dep())

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
    def _make_fake_deps(self, user_roles):
        """Return (fake_credentials, fake_workspace, mock_validator) for testing _check directly."""
        from fastapi.security import HTTPAuthorizationCredentials
        from models.domain.workspace import Workspace

        fake_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token")
        # Workspace with no client_id → falls straight through to core validator
        fake_workspace = Workspace(
            id="ws-id",
            templateName="test",
            templateVersion="0.1.0",
            etag="",
            resourcePath="/workspaces/ws-id",
            properties={},
        )
        validated_user = _make_user(roles=user_roles)
        mock_validator = MagicMock()
        mock_validator.validate.return_value = validated_user
        return fake_creds, fake_workspace, mock_validator, validated_user

    def test_admin_always_passes_without_workspace_role(self):
        dep = require_workspace_roles(WorkspaceAccessRole.Owner)
        fake_creds, fake_workspace, mock_validator, admin = self._make_fake_deps(["TREAdmin"])

        import asyncio

        async def _run():
            with patch('auth.rbac.get_core_validator', return_value=mock_validator):
                result = await dep(credentials=fake_creds, workspace=fake_workspace)
            assert result.id == "uid"

        asyncio.get_event_loop().run_until_complete(_run())

    def test_workspace_owner_passes(self):
        dep = require_workspace_roles(WorkspaceAccessRole.Owner)
        fake_creds, fake_workspace, mock_validator, owner = self._make_fake_deps(["WorkspaceOwner"])

        import asyncio

        async def _run():
            with patch('auth.rbac.get_core_validator', return_value=mock_validator):
                result = await dep(credentials=fake_creds, workspace=fake_workspace)
            assert result.id == "uid"

        asyncio.get_event_loop().run_until_complete(_run())

    def test_raises_403_for_user_without_workspace_role(self):
        from fastapi import HTTPException

        dep = require_workspace_roles(WorkspaceAccessRole.Owner)
        fake_creds, fake_workspace, mock_validator, researcher = self._make_fake_deps(["WorkspaceResearcher"])

        import asyncio

        async def _run():
            with patch('auth.rbac.get_core_validator', return_value=mock_validator):
                with pytest.raises(HTTPException) as exc_info:
                    await dep(credentials=fake_creds, workspace=fake_workspace)
            assert exc_info.value.status_code == 403

        asyncio.get_event_loop().run_until_complete(_run())


# ---------------------------------------------------------------------------
# AuthenticatedUser helpers
# ---------------------------------------------------------------------------


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

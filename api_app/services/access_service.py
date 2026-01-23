from abc import abstractmethod
from typing import List

from fastapi.security import OAuth2AuthorizationCodeBearer
from models.domain.workspace import Workspace, WorkspaceRole
from models.domain.authentication import User, RoleAssignment


class AuthConfigValidationError(Exception):
    """Raised when the input auth information is invalid"""


class UserRoleAssignmentError(Exception):
    """Raised when a user role assignment fails"""


class AccessService(OAuth2AuthorizationCodeBearer):
    @abstractmethod
    def extract_workspace_auth_information(self, data: dict) -> dict:
        pass

    @abstractmethod
    def get_identity_role_assignments(self, user_id: str) -> dict:
        pass

    @abstractmethod
    def get_workspace_users(self, workspace: Workspace) -> List[User]:
        pass

    @abstractmethod
    def get_workspace_user_emails_by_role_assignment(self, workspace: Workspace) -> dict:
        pass

    @staticmethod
    @abstractmethod
    def get_workspace_role(user: User, workspace: Workspace, user_role_assignments: List[RoleAssignment]) -> WorkspaceRole:
        pass

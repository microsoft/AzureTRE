from abc import ABC, abstractmethod
from services.authentication import User


class AuthConfigValidationError(Exception):
    """Raised when the input auth information is invalid"""


class AccessService(ABC):
    @abstractmethod
    def extract_workspace_auth_information(self, data: dict) -> dict:
        pass

    @abstractmethod
    def get_user_role_assignments(self, user: User):
        pass

from abc import ABC, abstractmethod


class AuthConfigValidationError(Exception):
    """Raised when the input auth information is invalid"""


class AccessService(ABC):
    @abstractmethod
    def extract_workspace_auth_information(self, data: dict) -> dict:
        pass

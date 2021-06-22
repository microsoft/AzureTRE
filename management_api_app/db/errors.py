class EntityDoesNotExist(Exception):
    """Raised when entity was not found in database."""


class UnableToAccessDatabase(Exception):
    """Raised when we can't access the database"""


class WorkspaceValidationError(Exception):
    """Raised when API request validation fails"""
    errors: dict

    def __init__(self, errors: dict):
        self.errors = errors

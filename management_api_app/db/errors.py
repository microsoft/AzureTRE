class EntityDoesNotExist(Exception):
    """Raised when entity was not found in database."""


class EntityVersionExist(Exception):
    """Raised when entity was not found in database."""


class UnableToAccessDatabase(Exception):
    """Raised when we can't access the database"""

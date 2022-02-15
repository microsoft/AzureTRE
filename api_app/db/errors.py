class EntityDoesNotExist(Exception):
    """Raised when entity was not found in database."""


class DuplicateEntity(Exception):
    """Raised when we have an unexpected duplicate (ex. two currents)"""


class EntityVersionExist(Exception):
    """Raised when entity was not found in database."""


class UnableToAccessDatabase(Exception):
    """Raised when we can't access the database"""


class ResourceIsNotDeployed(Exception):
    """Raised when trying to install resource under entity which haven't finalized its deployment."""


class InvalidInput(Exception):
    """Raised when invalid input is received when creating an entity."""

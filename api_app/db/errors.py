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


class UserNotAuthorizedToUseTemplate(Exception):
    """Raised when user attempts to use a template they aren't authorized to use"""


class MajorVersionUpdateDenied(Exception):
    """Raised when user attempts to update a resource with a major version."""


class TargetTemplateVersionDoesNotExist(Exception):
    """Raised when user attempts to upgrade a resource to a version which was not registered."""


class VersionDowngradeDenied(Exception):
    """Raised when user attempts to downgrade a resource to a lower version."""

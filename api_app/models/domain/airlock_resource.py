from enum import Enum
from resources import strings


# left for db migration
class AirlockResourceType(str, Enum):
    """
    Type of resource to create
    """
    AirlockRequest = strings.AIRLOCK_RESOURCE_TYPE_REQUEST
    AirlockReview = strings.AIRLOCK_RESOURCE_TYPE_REVIEW

from collections import defaultdict
from helpers import strings


# Specify pass and fail status strings so we can return the right statuses to the api depending on the action type (with a default of custom action)
failed_status_string_for = defaultdict(lambda: strings.RESOURCE_ACTION_STATUS_FAILED, {
    "install": strings.RESOURCE_STATUS_DEPLOYMENT_FAILED,
    "uninstall": strings.RESOURCE_STATUS_DELETING_FAILED,
    "upgrade": strings.RESOURCE_STATUS_UPDATING_FAILED
})

pass_status_string_for = defaultdict(lambda: strings.RESOURCE_ACTION_STATUS_SUCCEEDED, {
    "install": strings.RESOURCE_STATUS_DEPLOYED,
    "uninstall": strings.RESOURCE_STATUS_DELETED,
    "upgrade": strings.RESOURCE_STATUS_UPDATED
})

in_progress_status_string_for = defaultdict(lambda: strings.RESOURCE_ACTION_STATUS_INVOKING, {
    "install": strings.RESOURCE_STATUS_DEPLOYING,
    "uninstall": strings.RESOURCE_STATUS_DELETING,
    "upgrade": strings.RESOURCE_STATUS_UPDATING
})

from collections import defaultdict
from resources import strings


# Specify pass and fail status strings so we can return the right statuses to the api depending on the action type (with a default of custom action)
failed_status_string_for = defaultdict(lambda: strings.RESOURCE_ACTION_STATUS_FAILED, {
    "install": strings.RESOURCE_STATUS_FAILED,
    "uninstall": strings.RESOURCE_STATUS_DELETING_FAILED
})

pass_status_string_for = defaultdict(lambda: strings.RESOURCE_ACTION_STATUS_SUCCEEDED, {
    "install": strings.RESOURCE_STATUS_DEPLOYED,
    "uninstall": strings.RESOURCE_STATUS_DELETED
})

# RG
CORE_RESOURCE_GROUP_NAME = "rg-{}"
WORKSPACE_RESOURCE_GROUP_NAME = "rg-{}-ws-{}"

IMPORT_TYPE = "import"
EXPORT_TYPE = "export"

# Consolidated storage account names (metadata-based approach - Option B)
STORAGE_ACCOUNT_NAME_AIRLOCK_CORE = "stalairlock"  # Consolidated core account  
STORAGE_ACCOUNT_NAME_AIRLOCK_WORKSPACE_GLOBAL = "stalairlockg"  # Global workspace account (Option B)

# Stage metadata values for container metadata
STAGE_IMPORT_EXTERNAL = "import-external"
STAGE_IMPORT_IN_PROGRESS = "import-in-progress"
STAGE_IMPORT_APPROVED = "import-approved"
STAGE_IMPORT_REJECTED = "import-rejected"
STAGE_IMPORT_BLOCKED = "import-blocked"
STAGE_EXPORT_INTERNAL = "export-internal"
STAGE_EXPORT_IN_PROGRESS = "export-in-progress"
STAGE_EXPORT_APPROVED = "export-approved"
STAGE_EXPORT_REJECTED = "export-rejected"
STAGE_EXPORT_BLOCKED = "export-blocked"

# Legacy storage account names (for backwards compatibility)
# These will be removed after migration is complete
# Import
STORAGE_ACCOUNT_NAME_IMPORT_EXTERNAL = "stalimex"
STORAGE_ACCOUNT_NAME_IMPORT_INPROGRESS = "stalimip"
STORAGE_ACCOUNT_NAME_IMPORT_APPROVED = "stalimappws"
STORAGE_ACCOUNT_NAME_IMPORT_REJECTED = "stalimrej"
STORAGE_ACCOUNT_NAME_IMPORT_BLOCKED = "stalimblocked"

# Export
STORAGE_ACCOUNT_NAME_EXPORT_INTERNAL = "stalexintws"
STORAGE_ACCOUNT_NAME_EXPORT_INPROGRESS = "stalexipws"
STORAGE_ACCOUNT_NAME_EXPORT_APPROVED = "stalexapp"
STORAGE_ACCOUNT_NAME_EXPORT_REJECTED = "stalexrejws"
STORAGE_ACCOUNT_NAME_EXPORT_BLOCKED = "stalexblockedws"

# Stages
STAGE_DRAFT = "draft"
STAGE_SUBMITTED = "submitted"
STAGE_IN_REVIEW = "in_review"
STAGE_APPROVAL_INPROGRESS = "approval_in_progress"
STAGE_APPROVED = "approved"
STAGE_REJECTION_INPROGRESS = "rejection_in_progress"
STAGE_REJECTED = "rejected"
STAGE_CANCELLED = "cancelled"
STAGE_BLOCKING_INPROGRESS = "blocking_in_progress"
STAGE_BLOCKED_BY_SCAN = "blocked_by_scan"
STAGE_FAILED = "failed"

# Messages
NO_FILES_IN_REQUEST_MESSAGE = "Request did not contain any files."
TOO_MANY_FILES_IN_REQUEST_MESSAGE = "Request contained more than 1 file."
UNKNOWN_REASON_MESSAGE = "Request failed due to an unknown reason."

# Event Grid
STEP_RESULT_EVENT_DATA_VERSION = "1.0"
DATA_DELETION_EVENT_DATA_VERSION = "1.0"

NO_THREATS = "No threats found"

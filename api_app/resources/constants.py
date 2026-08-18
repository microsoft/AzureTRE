# RG
CORE_RESOURCE_GROUP_NAME = "rg-{}"
WORKSPACE_RESOURCE_GROUP_NAME = "rg-{}-ws-{}"

IMPORT_TYPE = "import"
EXPORT_TYPE = "export"

# New workspaces default to consolidated storage.
DEFAULT_AIRLOCK_VERSION = 2

STORAGE_ACCOUNT_NAME_AIRLOCK_CORE = "stalairlock{}"
STORAGE_ACCOUNT_NAME_AIRLOCK_WORKSPACE_GLOBAL = "stalairlockg{}"

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

# Retained during legacy storage migration.
# Import
STORAGE_ACCOUNT_NAME_IMPORT_EXTERNAL = "stalimex{}"
STORAGE_ACCOUNT_NAME_IMPORT_INPROGRESS = "stalimip{}"
STORAGE_ACCOUNT_NAME_IMPORT_APPROVED = "stalimappws{}"
STORAGE_ACCOUNT_NAME_IMPORT_REJECTED = "stalimrej{}"
STORAGE_ACCOUNT_NAME_IMPORT_BLOCKED = "stalimblocked{}"

# Export
STORAGE_ACCOUNT_NAME_EXPORT_INTERNAL = "stalexintws{}"
STORAGE_ACCOUNT_NAME_EXPORT_INPROGRESS = "stalexipws{}"
STORAGE_ACCOUNT_NAME_EXPORT_APPROVED = "stalexapp{}"
STORAGE_ACCOUNT_NAME_EXPORT_REJECTED = "stalexrejws{}"
STORAGE_ACCOUNT_NAME_EXPORT_BLOCKED = "stalexblockedws{}"

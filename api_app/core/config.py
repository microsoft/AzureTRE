from starlette.config import Config
from _version import __version__

config = Config(".env")

# API settings
API_PREFIX = "/api"
PROJECT_NAME: str = config("PROJECT_NAME", default="Azure TRE API")
DEBUG: bool = config("DEBUG", cast=bool, default=False)
ENABLE_LOCAL_DEBUGGING: bool = config("ENABLE_LOCAL_DEBUGGING", cast=bool, default=False)
ENABLE_SWAGGER: bool = config("ENABLE_SWAGGER", cast=bool, default=True)
VERSION = __version__
API_DESCRIPTION = "Welcome to the Azure TRE API - for more information about templates and workspaces see the [Azure TRE documentation](https://microsoft.github.io/AzureTRE)"

# Resource Info
RESOURCE_LOCATION: str = config("RESOURCE_LOCATION", default="")
TRE_ID: str = config("TRE_ID", default="")
CORE_ADDRESS_SPACE: str = config("CORE_ADDRESS_SPACE", default="")
TRE_ADDRESS_SPACE: str = config("TRE_ADDRESS_SPACE", default="")

# State store configuration
STATE_STORE_ENDPOINT: str = config("STATE_STORE_ENDPOINT", default="")      # Cosmos DB endpoint
STATE_STORE_SSL_VERIFY: bool = config("STATE_STORE_SSL_VERIFY", cast=bool, default=True)
STATE_STORE_KEY: str = config("STATE_STORE_KEY", default="")                # Cosmos DB access key
COSMOSDB_ACCOUNT_NAME: str = config("COSMOSDB_ACCOUNT_NAME", default="")                # Cosmos DB account name
STATE_STORE_DATABASE = "AzureTRE"
STATE_STORE_RESOURCES_CONTAINER = "Resources"
STATE_STORE_RESOURCE_TEMPLATES_CONTAINER = "ResourceTemplates"
STATE_STORE_RESOURCES_HISTORY_CONTAINER = "ResourceHistory"
STATE_STORE_OPERATIONS_CONTAINER = "Operations"
STATE_STORE_AIRLOCK_REQUESTS_CONTAINER = "Requests"
SUBSCRIPTION_ID: str = config("SUBSCRIPTION_ID", default="")
RESOURCE_GROUP_NAME: str = config("RESOURCE_GROUP_NAME", default="")


# Service bus configuration
SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE: str = config("SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE", default="")
SERVICE_BUS_RESOURCE_REQUEST_QUEUE: str = config("SERVICE_BUS_RESOURCE_REQUEST_QUEUE", default="")
SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE: str = config("SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE", default="")
SERVICE_BUS_STEP_RESULT_QUEUE: str = config("SERVICE_BUS_STEP_RESULT_QUEUE", default="")

# Event grid configuration
EVENT_GRID_STATUS_CHANGED_TOPIC_ENDPOINT: str = config("EVENT_GRID_STATUS_CHANGED_TOPIC_ENDPOINT", default="")
EVENT_GRID_AIRLOCK_NOTIFICATION_TOPIC_ENDPOINT: str = config("EVENT_GRID_AIRLOCK_NOTIFICATION_TOPIC_ENDPOINT", default="")

# Managed identity configuration
MANAGED_IDENTITY_CLIENT_ID: str = config("MANAGED_IDENTITY_CLIENT_ID", default="")

# Authentication
API_CLIENT_ID: str = config("API_CLIENT_ID", default="")
API_CLIENT_SECRET: str = config("API_CLIENT_SECRET", default="")
SWAGGER_UI_CLIENT_ID: str = config("SWAGGER_UI_CLIENT_ID", default="")
AAD_TENANT_ID: str = config("AAD_TENANT_ID", default="")

AAD_INSTANCE: str = config("AAD_INSTANCE", default="https://login.microsoftonline.com")
API_AUDIENCE: str = config("API_AUDIENCE", default=API_CLIENT_ID)

AIRLOCK_SAS_TOKEN_EXPIRY_PERIOD_IN_HOURS: int = config("AIRLOCK_SAS_TOKEN_EXPIRY_PERIOD_IN_HOURS", default=1)

API_ROOT_SCOPE: str = f"api://{API_CLIENT_ID}/user_impersonation"

# Notify UK Platform
NOTIFY_UK_TEMPLATE_ID: str = config("NOTIFY_UK_TEMPLATE_ID", default="")
NOTIFY_UK_URL: str = config("NOTIFY_UK_URL", default="")
NOTIFY_UK_SECRET: str = config("NOTIFY_UK_SECRET", default="")
NOTIFY_UK_ISS_ID: str = config("NOTIFY_UK_ISS_ID", default="")
NOTIFY_UK_EMAIL_SUBJECT_TAG: str = config("NOTIFY_UK_EMAIL_SUBJECT_TAG", default="")

# Triage level due date
DUE_DATE_DAYS_TO_ADD: map = config("DUE_DATE_DAYS_TO_ADD", default={"L1": 3, "L2": 5, "L2a": 5, "L2b": 15, "L3": 15, "L4": 0})
BANK_HOLIDAYS_FILE_PATH = "/api/resources/bank-holidays.json"

# Custom header for setting ClientType
CLIENT_TYPE_CUSTOM_HEADER: str = config("CLIENT_TYPE_CUSTOM_HEADER", default="")

from typing import List
import warnings
from starlette.config import Config
from _version import __version__

warnings.filterwarnings("ignore", message="Config file '.env' not found.")

config = Config('.env')

# API settings
API_PREFIX = "/api"
PROJECT_NAME: str = config("PROJECT_NAME", default="Azure TRE API")
LOGGING_LEVEL: str = config("LOGGING_LEVEL", default="INFO")
ENABLE_LOCAL_DEBUGGING: bool = config("ENABLE_LOCAL_DEBUGGING", cast=bool, default=False)
ENABLE_SWAGGER: bool = config("ENABLE_SWAGGER", cast=bool, default=False)
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

# Cloud configuration
AAD_AUTHORITY_URL: str = config("AAD_AUTHORITY_URL", default="https://login.microsoftonline.com")
RESOURCE_MANAGER_ENDPOINT: str = config("RESOURCE_MANAGER_ENDPOINT", default="https://management.azure.com")
CREDENTIAL_SCOPES: List[str] = [f"{RESOURCE_MANAGER_ENDPOINT}/.default"]
MICROSOFT_GRAPH_URL: str = config("MICROSOFT_GRAPH_URL", default="https://graph.microsoft.com")
STORAGE_ENDPOINT_SUFFIX: str = config("STORAGE_ENDPOINT_SUFFIX", default="core.windows.net")

# Monitoring
APPLICATIONINSIGHTS_CONNECTION_STRING: str = config("APPLICATIONINSIGHTS_CONNECTION_STRING", default=None)

# Authentication
API_CLIENT_ID: str = config("API_CLIENT_ID", default="")
API_CLIENT_SECRET: str = config("API_CLIENT_SECRET", default="")
SWAGGER_UI_CLIENT_ID: str = config("SWAGGER_UI_CLIENT_ID", default="")
AAD_TENANT_ID: str = config("AAD_TENANT_ID", default="")

API_AUDIENCE: str = config("API_AUDIENCE", default=API_CLIENT_ID)

AIRLOCK_SAS_TOKEN_EXPIRY_PERIOD_IN_HOURS: int = config("AIRLOCK_SAS_TOKEN_EXPIRY_PERIOD_IN_HOURS", default=1)
ENABLE_AIRLOCK_EMAIL_CHECK: bool = config("ENABLE_AIRLOCK_EMAIL_CHECK", cast=bool, default=False)

API_ROOT_SCOPE: str = f"api://{API_CLIENT_ID}/user_impersonation"

# User Management
USER_MANAGEMENT_ENABLED: bool = config("USER_MANAGEMENT_ENABLED", cast=bool, default=False)

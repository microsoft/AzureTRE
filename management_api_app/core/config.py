from starlette.config import Config


config = Config(".env")

# API settings
API_PREFIX = "/api"
PROJECT_NAME: str = config("PROJECT_NAME", default="Azure TRE API")
DEBUG: bool = config("DEBUG", cast=bool, default=False)
VERSION = "0.0.0"

# Resource Info
RESOURCE_LOCATION: str = config("RESOURCE_LOCATION", default="")
TRE_ID: str = config("TRE_ID", default="")

# State store configuration
STATE_STORE_ENDPOINT: str = config("STATE_STORE_ENDPOINT", default="")      # Cosmos DB endpoint
STATE_STORE_KEY: str = config("STATE_STORE_KEY", default="")                # Cosmos DB access key
STATE_STORE_DATABASE = "AzureTRE"
STATE_STORE_RESOURCES_CONTAINER = "Resources"
STATE_STORE_RESOURCE_TEMPLATES_CONTAINER = "ResourceTemplates"

# Service bus configuration
SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE: str = config("SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE", default="")
SERVICE_BUS_RESOURCE_REQUEST_QUEUE: str = config("SERVICE_BUS_RESOURCE_REQUEST_QUEUE", default="")

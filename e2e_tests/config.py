from starlette.config import Config


config = Config(".env")

# Resource Info
RESOURCE_LOCATION: str = config("RESOURCE_LOCATION", default="")
TRE_ID: str = config("TRE_ID", default="")
RESOURCE: str = config("RESOURCE", default="")
USERNAME: str = config("USERNAME", default="")
PASSWORD: str = config("PASSWORD", default="")
SCOPE: str = config("SCOPE", default="")
CLIENT_ID: str = config("CLIENT_ID", default="")
AUTH_TENANT_ID: str = config("AUTH_TENANT_ID", default="")
AUTH_APP_CLIENT_ID: str = config("AUTH_APP_CLIENT_ID", default="")

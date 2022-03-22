from starlette.config import Config


config = Config(".env")

# Resource Info
RESOURCE_LOCATION: str = config("RESOURCE_LOCATION", default="")
TRE_ID: str = config("TRE_ID", default="")
API_CLIENT_ID: str = config("API_CLIENT_ID", default="")
TEST_USER_NAME: str = config("TEST_USER_NAME", default="")
TEST_USER_PASSWORD: str = config("TEST_USER_PASSWORD", default="")
TEST_APP_ID: str = config("TEST_APP_ID", default="")
AAD_TENANT_ID: str = config("AAD_TENANT_ID", default="")
TEST_ACCOUNT_CLIENT_ID: str = config("TEST_ACCOUNT_CLIENT_ID", default="")
TEST_ACCOUNT_CLIENT_SECRET: str = config("TEST_ACCOUNT_CLIENT_SECRET", default="")
TEST_WORKSPACE_APP_ID: str = config("TEST_WORKSPACE_APP_ID", default="")

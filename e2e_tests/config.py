import warnings
from starlette.config import Config

warnings.filterwarnings("ignore", message="Config file '.env' not found.")

config = Config('.env')

# Resource Info
RESOURCE_LOCATION: str = config("RESOURCE_LOCATION", default="")
TRE_ID: str = config("TRE_ID", default="")
TRE_URL: str = config("TRE_URL", default="")
API_CLIENT_ID: str = config("API_CLIENT_ID", default="")
TEST_USER_NAME: str = config("TEST_USER_NAME", default="")
TEST_USER_PASSWORD: str = config("TEST_USER_PASSWORD", default="")
TEST_APP_ID: str = config("TEST_APP_ID", default="")
AAD_TENANT_ID: str = config("AAD_TENANT_ID", default="")
TEST_ACCOUNT_CLIENT_ID: str = config("TEST_ACCOUNT_CLIENT_ID", default="")
TEST_ACCOUNT_CLIENT_SECRET: str = config("TEST_ACCOUNT_CLIENT_SECRET", default="")
TEST_WORKSPACE_APP_ID: str = config("TEST_WORKSPACE_APP_ID", default="")
TEST_WORKSPACE_APP_SECRET: str = config("TEST_WORKSPACE_APP_SECRET", default="")
TEST_WORKSPACE_APP_PLAN: str = config("WORKSPACE_APP_SERVICE_PLAN_SKU", default="")

# Set workspace id of an existing workspace to skip creation of a workspace during E2E tests
TEST_WORKSPACE_ID: str = config("TEST_WORKSPACE_ID", default="")
TEST_WORKSPACE_SERVICE_ID: str = config("TEST_WORKSPACE_SERVICE_ID", default="")
TEST_AAD_WORKSPACE_ID: str = config("TEST_AAD_WORKSPACE_ID", default="")
TEST_AIRLOCK_IMPORT_REVIEW_WORKSPACE_ID: str = config("TEST_AIRLOCK_IMPORT_REVIEW_WORKSPACE_ID", default="")
TEST_AIRLOCK_IMPORT_REVIEW_WORKSPACE_SERVICE_ID: str = config("TEST_AIRLOCK_IMPORT_REVIEW_WORKSPACE_SERVICE_ID", default="")

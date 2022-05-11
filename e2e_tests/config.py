from starlette.config import Config


config = Config(".env")

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

# Perf test env vars - set these in private.env if you want to run perf tests and use an existing
# workspace + workspace service for quicker execution. If they're blank the perf test will create + delete them.
PERF_TEST_WORKSPACE_ID: str = config("PERF_TEST_WORKSPACE_ID", default="")
PERF_TEST_WORKSPACE_SERVICE_ID: str = config("PERF_TEST_WORKSPACE_SERVICE_ID", default="")

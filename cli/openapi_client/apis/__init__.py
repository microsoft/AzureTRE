
# flake8: noqa

# Import all APIs into this package.
# If you have many APIs here with many many models used in each API this may
# raise a `RecursionError`.
# In order to avoid this, import only the API that you directly need like:
#
#   from openapi_client.api.health_api import HealthApi
#
# or import this package, but before doing it, use:
#
#   import sys
#   sys.setrecursionlimit(n)

# Import APIs into API package:
from openapi_client.api.health_api import HealthApi
from openapi_client.api.shared_service_templates_api import SharedServiceTemplatesApi
from openapi_client.api.shared_services_api import SharedServicesApi
from openapi_client.api.user_resource_templates_api import UserResourceTemplatesApi
from openapi_client.api.workspace_service_templates_api import WorkspaceServiceTemplatesApi
from openapi_client.api.workspace_templates_api import WorkspaceTemplatesApi
from openapi_client.api.workspaces_api import WorkspacesApi

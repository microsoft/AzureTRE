PONG = "pong"

# API Descriptions
API_GET_HEALTH_STATUS = "Get health status"

API_GET_ALL_WORKSPACES = "Get all workspaces"
API_GET_WORKSPACE_BY_ID = "Get workspace by Id"
API_CREATE_WORKSPACE = "Create a workspace"

API_GET_STATUS_OF_SERVICES = "Get status of services"

API_GET_WORKSPACE_TEMPLATES = "Get workspace template names"
API_CREATE_WORKSPACE_TEMPLATES = "Create workspace template"
API_GET_WORKSPACE_TEMPLATE_BY_NAME = "Get workspace template by name"

# State store status
OK = "OK"
NOT_OK = "Not OK"
COSMOS_DB = "Cosmos DB"
STATE_STORE_ENDPOINT_NOT_RESPONDING = "State Store endpoint is not responding"
UNSPECIFIED_ERROR = "Unspecified error"

# Error strings
WORKSPACE_DOES_NOT_EXIST = "Workspace does not exist"
WORKSPACE_TEMPLATE_DOES_NOT_EXIST = "Workspace template does not exist"
WORKSPACE_TEMPLATE_VERSION_EXISTS = "A template with this version already exists"

# Resource Status
RESOURCE_STATUS_NOT_DEPLOYED = "not_deployed"
RESOURCE_STATUS_DEPLOYING = "deploying"
RESOURCE_STATUS_DEPLOYED = "deployed"
RESOURCE_STATUS_DELETING = "deleting"
RESOURCE_STATUS_DELETED = "deleted"

# Resource Type
RESOURCE_TYPE_WORKSPACE = "workspace"
RESOURCE_TYPE_SERVICE = "service"

# Deployments
RESOURCE_STATUS_NOT_DEPLOYED_MESSAGE = "This resource has not yet been deployed"

# Service bus
SERVICE_BUS_GENERAL_ERROR_MESSAGE = "Service bus failure"
DEPLOYMENT_STATUS_MESSAGE_FORMAT_INCORRECT = "Service bus message is not formatted correctly."
DEPLOYMENT_STATUS_ID_NOT_FOUND = "Service bus message refers to resource which does not exist"

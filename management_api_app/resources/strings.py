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
ACCESS_APP_IS_MISSING_ROLE = "The App is missing role"
ACCESS_PLEASE_SUPPLY_APP_ID = "Please supply the app_id for the AAD application"
ACCESS_UNABLE_TO_GET_INFO_FOR_APP = "Unable to get app info for app:"
ACCESS_UNABLE_TO_GET_ROLE_ASSIGNMENTS_FOR_USER = "Unable to get role assignments for user"
ACCESS_USER_IS_NOT_OWNER_OR_RESEARCHER = "Researcher or Owner rights required to see workspace details"
AUTH_NOT_ASSIGNED_TO_ADMIN_ROLE = "Not assigned to admin role"
AUTH_COULD_NOT_VALIDATE_CREDENTIALS = "Could not validate credentials"
AUTH_CONFIGURATION_NOT_AVAILABLE_FOR_WORKSPACE = "Auth configuration not available for workspace"
INVALID_AUTH_PROVIDER = "Invalid authentication provider"
UNABLE_TO_REPLACE_CURRENT_TEMPLATE = "Unable to replace the existing 'current' template with this name"
UNABLE_TO_PROCESS_REQUEST = "Unable to process request"
WORKSPACE_DOES_NOT_EXIST = "Workspace does not exist"
WORKSPACE_TEMPLATE_DOES_NOT_EXIST = "Could not retrieve the 'current' template with this name"
WORKSPACE_TEMPLATE_VERSION_EXISTS = "A template with this version already exists"


# Resource Status
RESOURCE_STATUS_NOT_DEPLOYED = "not_deployed"
RESOURCE_STATUS_DEPLOYING = "deploying"
RESOURCE_STATUS_DEPLOYED = "deployed"
RESOURCE_STATUS_DELETING = "deleting"
RESOURCE_STATUS_DELETED = "deleted"
RESOURCE_STATUS_FAILED = "failed"

# Resource Type
RESOURCE_TYPE_WORKSPACE = "workspace"
RESOURCE_TYPE_SERVICE = "service"

# Deployments
RESOURCE_STATUS_NOT_DEPLOYED_MESSAGE = "This resource has not yet been deployed"

# Service bus
SERVICE_BUS_GENERAL_ERROR_MESSAGE = "Service bus failure"
DEPLOYMENT_STATUS_MESSAGE_FORMAT_INCORRECT = "Service bus message is not formatted correctly"
DEPLOYMENT_STATUS_ID_NOT_FOUND = "Service bus message refers to resource id = {} which does not exist"

# Workspace creation validation
MISSING_REQUIRED_PARAMETERS = "Missing required parameters"
INVALID_EXTRA_PARAMETER = "Invalid extra parameters"
PARAMETERS_WITH_WRONG_TYPE = "Parameters with wrong type"

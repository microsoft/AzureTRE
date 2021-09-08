PONG = "pong"

# API Descriptions
API_GET_HEALTH_STATUS = "Get health status"

API_GET_ALL_WORKSPACES = "Get all workspaces [ADMIN + WORKSPACE OWNER/RESEARCHER]"
API_GET_WORKSPACE_BY_ID = "Get workspace by Id [ADMIN + WORKSPACE OWNER/RESEARCHER]"
API_CREATE_WORKSPACE = "Create a workspace [ADMIN]"
API_DELETE_WORKSPACE = "Delete workspace [ADMIN]"
API_UPDATE_WORKSPACE = "Update an existing workspace [ADMIN]"

API_GET_ALL_WORKSPACE_SERVICES = "Get all workspace services for workspace [WORKSPACE OWNER/RESEARCHER]"
API_GET_WORKSPACE_SERVICE_BY_ID = "Get workspace service by Id [WORKSPACE OWNER/RESEARCHER]"
API_CREATE_WORKSPACE_SERVICE = "Create a workspace service [WORKSPACE OWNER]"
API_UPDATE_WORKSPACE_SERVICE = "Update an existing workspace service [WORKSPACE OWNER]"

API_CREATE_USER_RESOURCE = "Create a user resource [WORKSPACE RESEARCHER]"
API_GET_MY_USER_RESOURCES = "Get my user resources in the workspace service [WORKSPACE RESEARCHER]"
API_GET_USER_RESOURCE = "Get user resource by id [WORKSPACE RESEARCHER]"

API_GET_STATUS_OF_SERVICES = "Get status of services"

API_CREATE_WORKSPACE_TEMPLATES = "Register workspace template [ADMIN]"
API_GET_WORKSPACE_TEMPLATES = "Get workspace templates [ADMIN]"
API_GET_WORKSPACE_TEMPLATE_BY_NAME = "Get workspace template by name [ADMIN]"

API_CREATE_WORKSPACE_SERVICE_TEMPLATES = "Register workspace service template [ADMIN]"
API_GET_WORKSPACE_SERVICE_TEMPLATES = "Get workspace service templates [ALL TRE USERS]"
API_GET_WORKSPACE_SERVICE_TEMPLATE_BY_NAME = "Get workspace service template by name [ALL TRE USERS]"

API_CREATE_USER_RESOURCE_TEMPLATES = "Register user resource template [ADMIN]"
API_GET_USER_RESOURCE_TEMPLATES = "Get user resource templates applicable to the workspace service template [ALL TRE USERS]"
API_GET_USER_RESOURCE_TEMPLATE_BY_NAME = "Get user resource template by name and workspace service [ALL TRE USERS]"

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
ACCESS_USER_IS_NOT_OWNER = "Owner rights required to install workspace service"
AUTH_NOT_ASSIGNED_TO_ADMIN_ROLE = "Not assigned to admin role"
AUTH_COULD_NOT_VALIDATE_CREDENTIALS = "Could not validate credentials"
AUTH_CONFIGURATION_NOT_AVAILABLE_FOR_WORKSPACE = "Auth configuration not available for workspace"
INVALID_AUTH_PROVIDER = "Invalid authentication provider"
UNABLE_TO_REPLACE_CURRENT_TEMPLATE = "Unable to replace the existing 'current' template with this name"
UNABLE_TO_PROCESS_REQUEST = "Unable to process request"
USER_RESOURCE_DOES_NOT_EXIST = "User Resource does not exist"
WORKSPACE_DOES_NOT_EXIST = "Workspace does not exist"
WORKSPACE_IS_NOT_DEPLOYED = "Workspace is not deployed."
WORKSPACE_SERVICE_DOES_NOT_EXIST = "Workspace service does not exist"
WORKSPACE_SERVICE_IS_NOT_DEPLOYED = "Workspace service is not deployed."
WORKSPACE_NEEDS_TO_BE_DISABLED_BEFORE_DELETION = "The workspace needs to be disabled before you can delete it"
WORKSPACE_SERVICES_NEED_TO_BE_DELETED_BEFORE_WORKSPACE = "All workspace services need to be deleted before you can delete the workspace"
TEMPLATE_DOES_NOT_EXIST = "Could not retrieve the 'current' template with this name"
WORKSPACE_TEMPLATE_VERSION_EXISTS = "A template with this version already exists"
NO_UNIQUE_CURRENT_FOR_TEMPLATE = "The template has multiple 'current' versions"

# Resource Status
RESOURCE_STATUS_NOT_DEPLOYED = "not_deployed"
RESOURCE_STATUS_DEPLOYING = "deploying"
RESOURCE_STATUS_DEPLOYED = "deployed"
RESOURCE_STATUS_DELETING = "deleting"
RESOURCE_STATUS_DELETED = "deleted"
RESOURCE_STATUS_FAILED = "failed"
RESOURCE_STATUS_DELETING_FAILED = "deleting_failed"

# Resource Type
RESOURCE_TYPE_WORKSPACE = "workspace"
RESOURCE_TYPE_WORKSPACE_SERVICE = "workspace-service"
USER_RESOURCE = "user-resource"

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

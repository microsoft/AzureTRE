PONG = "pong"

# API Descriptions
API_GET_HEALTH_STATUS = "Get health status"
API_MIGRATE_DATABASE = "Migrate documents in the database"

API_GET_ALL_WORKSPACES = "Get all workspaces"
API_GET_WORKSPACE_BY_ID = "Get workspace by Id"
API_CREATE_WORKSPACE = "Create a workspace"
API_DELETE_WORKSPACE = "Delete workspace"
API_UPDATE_WORKSPACE = "Update an existing workspace"
API_INVOKE_ACTION_ON_WORKSPACE = "Invoke action on a workspace"

API_GET_ALL_WORKSPACE_SERVICES = "Get all workspace services for workspace"
API_GET_WORKSPACE_SERVICE_BY_ID = "Get workspace service by Id"
API_CREATE_WORKSPACE_SERVICE = "Create a workspace service"
API_UPDATE_WORKSPACE_SERVICE = "Update an existing workspace service"
API_DELETE_WORKSPACE_SERVICE = "Delete workspace service"
API_INVOKE_ACTION_ON_WORKSPACE_SERVICE = "Invoke action on a workspace service"
API_GET_RESOURCE_OPERATIONS = "Get all operations for a resource"
API_GET_RESOURCE_OPERATION_BY_ID = "Get a single resource operation by id"

API_CREATE_USER_RESOURCE = "Create a user resource"
API_GET_MY_USER_RESOURCES = "Get my user resources in the workspace service"
API_GET_USER_RESOURCE = "Get user resource by id"
API_DELETE_USER_RESOURCE = "Delete user resource"
API_UPDATE_USER_RESOURCE = "Update an existing user resource"
API_INVOKE_ACTION_ON_USER_RESOURCE = "Invoke action on a user resource"

API_CREATE_WORKSPACE_TEMPLATES = "Register workspace template"
API_GET_WORKSPACE_TEMPLATES = "Get workspace templates"
API_GET_WORKSPACE_TEMPLATE_BY_NAME = "Get workspace template by name"

API_CREATE_WORKSPACE_SERVICE_TEMPLATES = "Register workspace service template"
API_GET_WORKSPACE_SERVICE_TEMPLATES = "Get workspace service templates"
API_GET_WORKSPACE_SERVICE_TEMPLATE_BY_NAME = "Get workspace service template by name"

API_CREATE_SHARED_SERVICE_TEMPLATES = "Register shared service template"
API_GET_SHARED_SERVICE_TEMPLATES = "Get shared service templates"
API_GET_SHARED_SERVICE_TEMPLATE_BY_NAME = "Get shared service template by name"

API_GET_ALL_SHARED_SERVICES = "Get all shared services"
API_GET_SHARED_SERVICE_BY_ID = "Get shared service by ID"
API_CREATE_SHARED_SERVICE = "Create a shared service"
API_UPDATE_SHARED_SERVICE = "Update an existing shared service"
API_DELETE_SHARED_SERVICE = "Delete shared service"
API_INVOKE_ACTION_ON_SHARED_SERVICE = "Invoke action on a shared service"

API_CREATE_USER_RESOURCE_TEMPLATES = "Register user resource template"
API_GET_USER_RESOURCE_TEMPLATES = "Get user resource templates applicable to the workspace service template"
API_GET_USER_RESOURCE_TEMPLATE_BY_NAME = "Get user resource template by name and workspace service"

# State store status
OK = "OK"
NOT_OK = "Not OK"
COSMOS_DB = "Cosmos DB"
STATE_STORE_ENDPOINT_NOT_RESPONDING = "State Store endpoint is not responding"
UNSPECIFIED_ERROR = "Unspecified error"

# Service bus status
SERVICE_BUS = "Service Bus"
SERVICE_BUS_NOT_RESPONDING = "Service Bus is not responding"

# Resource processor status
RESOURCE_PROCESSOR = "Resource Processor"
RESOURCE_PROCESSOR_GENERAL_ERROR_MESSAGE = "Resource Processor is not responding"
RESOURCE_PROCESSOR_HEALTHY_MESSAGE = "HealthState/healthy"

# Error strings
ACCESS_APP_IS_MISSING_ROLE = "The App is missing role"
ACCESS_PLEASE_SUPPLY_CLIENT_ID = "Please supply the client_id for the AAD application"
ACCESS_UNABLE_TO_GET_INFO_FOR_APP = "Unable to get app info for app:"
ACCESS_UNABLE_TO_GET_ROLE_ASSIGNMENTS_FOR_USER = "Unable to get role assignments for user"

ACCESS_USER_IS_NOT_OWNER_OR_RESEARCHER = "Workspace Researcher or Owner rights are required"
ACCESS_USER_IS_NOT_OWNER = "Workspace Owner rights are required"
ACCESS_USER_DOES_NOT_HAVE_REQUIRED_ROLE = "The user is missing a required role"

AUTH_NOT_ASSIGNED_TO_ADMIN_ROLE = "Not assigned to admin role"
AUTH_COULD_NOT_VALIDATE_CREDENTIALS = "Could not validate credentials"
AUTH_CONFIGURATION_NOT_AVAILABLE_FOR_WORKSPACE = "Auth configuration not available for workspace"
AUTH_UNABLE_TO_VALIDATE_TOKEN = "Unable to decode or validate token"
INVALID_AUTH_PROVIDER = "Invalid authentication provider"

UNABLE_TO_REPLACE_CURRENT_TEMPLATE = "Unable to replace the existing 'current' template with this name"
UNABLE_TO_PROCESS_REQUEST = "Unable to process request"

USER_RESOURCE_DOES_NOT_EXIST = "User Resource does not exist"
USER_RESOURCES_NEED_TO_BE_DELETED_BEFORE_WORKSPACE = "All user resources need to be deleted before you can delete the workspace service"
USER_RESOURCE_NEEDS_TO_BE_DISABLED_BEFORE_DELETION = "The resource needs to be disabled before you can delete it"

WORKSPACE_DOES_NOT_EXIST = "Workspace does not exist"
WORKSPACE_IS_NOT_DEPLOYED = "Workspace is not deployed."
WORKSPACE_NEEDS_TO_BE_DISABLED_BEFORE_DELETION = "The workspace needs to be disabled before you can delete it"

WORKSPACE_SERVICE_DOES_NOT_EXIST = "Workspace service does not exist"
WORKSPACE_SERVICE_IS_NOT_DEPLOYED = "Workspace service is not deployed."
WORKSPACE_SERVICE_NEEDS_TO_BE_DISABLED_BEFORE_DELETION = "The workspace service needs to be disabled before you can delete it"
WORKSPACE_SERVICES_NEED_TO_BE_DELETED_BEFORE_WORKSPACE = "All workspace services need to be deleted before you can delete the workspace"
WORKSPACE_TEMPLATE_VERSION_EXISTS = "A template with this version already exists"
OPERATION_DOES_NOT_EXIST = "Operation does not exist"
CUSTOM_ACTION_NOT_DEFINED = "The specified custom action isn't defined in the targeted resource."
CUSTOM_ACTIONS_DO_NOT_EXIST = "The resource being targeted does not implement any custom actions."

WORKSPACE_SERVICE_TEMPLATE_DOES_NOT_EXIST = "Could not retrieve the workspace service template specified"
TEMPLATE_DOES_NOT_EXIST = "Could not retrieve the 'current' template with this name"
NO_UNIQUE_CURRENT_FOR_TEMPLATE = "The template has multiple 'current' versions"

SHARED_SERVICE_DOES_NOT_EXIST = "Shared service does not exist"
SHARED_SERVICE_NEEDS_TO_BE_DISABLED_BEFORE_DELETION = "Shared service needs to be disabled before you can delete it"

SHARED_SERVICE_TEMPLATE_DOES_NOT_EXIST = "Could not retrieve the workspace service template specified"
SHARED_SERVICE_TEMPLATE_VERSION_EXISTS = "A template with this version already exists"

ETAG_REQUIRED = "A valid etag must be supplied in the header of this request"
ETAG_CONFLICT = "This document has been modified by another user or process since you last retrieved it. Please get the document again and retry."

# Resource Status
RESOURCE_STATUS_NOT_DEPLOYED = "not_deployed"
RESOURCE_STATUS_DEPLOYING = "deploying"
RESOURCE_STATUS_DEPLOYED = "deployed"
RESOURCE_STATUS_DELETING = "deleting"
RESOURCE_STATUS_DELETED = "deleted"
RESOURCE_STATUS_FAILED = "failed"
RESOURCE_STATUS_DELETING_FAILED = "deleting_failed"

# Resource Action Status
RESOURCE_ACTION_STATUS_INVOKING = "invoking_action"
RESOURCE_ACTION_STATUS_SUCCEEDED = "action_succeeded"
RESOURCE_ACTION_STATUS_FAILED = "action_failed"

# Pipeline (multi-step) deployments
RESOURCE_ACTION_STATUS_PIPELINE_DEPLOYING = "pipeline_deploying"
RESOURCE_ACTION_STATUS_PIPELINE_FAILED = "pipeline_failed"
RESOURCE_ACTION_STATUS_PIPELINE_SUCCEEDED = "pipeline_succeeded"

# Resource Type
RESOURCE_TYPE_WORKSPACE = "workspace"
RESOURCE_TYPE_WORKSPACE_SERVICE = "workspace-service"
USER_RESOURCE = "user-resource"
RESOURCE_TYPE_SHARED_SERVICE = "shared-service"

# Deployments
RESOURCE_STATUS_NOT_DEPLOYED_MESSAGE = "This resource has not yet been deployed"
RESOURCE_STATUS_UPGRADE_NOT_STARTED_MESSAGE = "The upgrade for this resource has not yet started"

# Service bus
SERVICE_BUS_GENERAL_ERROR_MESSAGE = "Service bus failure"
DEPLOYMENT_STATUS_MESSAGE_FORMAT_INCORRECT = "Service bus message is not formatted correctly"
DEPLOYMENT_STATUS_ID_NOT_FOUND = "Service bus message refers to resource id = {} which does not exist"

# Workspace creation validation
MISSING_REQUIRED_PARAMETERS = "Missing required parameters"
INVALID_EXTRA_PARAMETER = "Invalid extra parameters"
PARAMETERS_WITH_WRONG_TYPE = "Parameters with wrong type"

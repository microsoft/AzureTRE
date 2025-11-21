PONG = "pong"

# API Descriptions
API_GET_HEALTH_STATUS = "Get health status"
API_GET_PING = "Simple endpoint to test calling the API"
API_GET_METADATA = "Get public API metadata (e.g. to support the UI and CLI)"
API_MIGRATE_DATABASE = "Migrate documents in the database"

API_GET_MY_OPERATIONS = "Get Operations that the current user has initiated"
API_GET_ALL_WORKSPACES = "Get all workspaces"
API_GET_WORKSPACE_BY_ID = "Get workspace by Id"
API_GET_WORKSPACE_SCOPE_ID_BY_WORKSPACE_ID = "Get workspace Scope Id by workspace Id"
API_CREATE_WORKSPACE = "Create a workspace"
API_DELETE_WORKSPACE = "Delete workspace"
API_UPDATE_WORKSPACE = "Update an existing workspace"
API_INVOKE_ACTION_ON_WORKSPACE = "Invoke action on a workspace"

API_GET_WORKSPACE_USERS = "Get all users for a workspace"
API_GET_ASSIGNABLE_USERS = "Get all users assignable to a workspace"
API_GET_WORKSPACE_ROLES = "Get all the roles belonging to a workspace"
API_ASSIGN_WORKSPACE_USER = "Assign a user to a workspace role"
API_REMOVE_WORKSPACE_USER_ASSIGNMENT = "Remove a user from a workspace role"

API_GET_ALL_WORKSPACE_SERVICES = "Get all workspace services for workspace"
API_GET_WORKSPACE_SERVICE_BY_ID = "Get workspace service by Id"
API_CREATE_WORKSPACE_SERVICE = "Create a workspace service"
API_UPDATE_WORKSPACE_SERVICE = "Update an existing workspace service"
API_DELETE_WORKSPACE_SERVICE = "Delete workspace service"
API_INVOKE_ACTION_ON_WORKSPACE_SERVICE = "Invoke action on a workspace service"
API_GET_RESOURCE_OPERATIONS = "Get all operations for a resource"
API_GET_RESOURCE_OPERATION_BY_ID = "Get a single resource operation by id"
API_GET_RESOURCE_HISTORY = "Get history for a resource"

API_CREATE_USER_RESOURCE = "Create a user resource"
API_GET_MY_USER_RESOURCES = "Get my user resources in the workspace service"
API_GET_USER_RESOURCE = "Get user resource by id"
API_DELETE_USER_RESOURCE = "Delete user resource"
API_UPDATE_USER_RESOURCE = "Update an existing user resource"
API_INVOKE_ACTION_ON_USER_RESOURCE = "Invoke action on a user resource"

API_LIST_REQUESTS = "Get requests"

API_CREATE_AIRLOCK_REQUEST = "Create an airlock request"
API_GET_AIRLOCK_REQUEST = "Get an airlock request"
API_LIST_AIRLOCK_REQUESTS = "Get all airlock requests for a workspace"
API_SUBMIT_AIRLOCK_REQUEST = "Submit an airlock request"
API_CANCEL_AIRLOCK_REQUEST = "Cancel an airlock request"
API_REVIEW_AIRLOCK_REQUEST = "Review an airlock request"
API_REVOKE_AIRLOCK_REQUEST = "Revoke an airlock request"
API_AIRLOCK_REQUEST_LINK = "Get a token to access airlock request"
API_CREATE_AIRLOCK_REVIEW_USER_RESOURCE = "Create an Airlock Review User Resource"

API_CREATE_WORKSPACE_TEMPLATES = "Register workspace template"
API_GET_WORKSPACE_TEMPLATES = "Get workspace templates"
API_GET_WORKSPACE_TEMPLATE_BY_NAME = "Get workspace template by name and optional version"

API_CREATE_WORKSPACE_SERVICE_TEMPLATES = "Register workspace service template"
API_GET_WORKSPACE_SERVICE_TEMPLATES = "Get workspace service templates"
API_GET_WORKSPACE_SERVICE_TEMPLATES_IN_WORKSPACE = "Get workspace service templates (on workspace level)"  # only returns templates that the authenticated user is authorized to use
API_GET_WORKSPACE_SERVICE_TEMPLATE_BY_NAME = "Get workspace service template by name and optional version"

API_CREATE_SHARED_SERVICE_TEMPLATES = "Register shared service template"
API_GET_SHARED_SERVICE_TEMPLATES = "Get shared service templates"
API_GET_SHARED_SERVICE_TEMPLATE_BY_NAME = "Get shared service template by name and optional version"

API_GET_ALL_SHARED_SERVICES = "Get all shared services"
API_GET_SHARED_SERVICE_BY_ID = "Get shared service by ID"
API_CREATE_SHARED_SERVICE = "Create a shared service"
API_UPDATE_SHARED_SERVICE = "Update an existing shared service"
API_DELETE_SHARED_SERVICE = "Delete shared service"
API_INVOKE_ACTION_ON_SHARED_SERVICE = "Invoke action on a shared service"

API_CREATE_USER_RESOURCE_TEMPLATES = "Register user resource template"
API_GET_USER_RESOURCE_TEMPLATES = "Get user resource templates applicable to the workspace service template"
API_GET_USER_RESOURCE_TEMPLATES_IN_WORKSPACE = "Get user resource templates applicable to the workspace service template (on workspace level)"  # only returns templates that the authenticated user is authorized to use
API_GET_USER_RESOURCE_TEMPLATE_BY_NAME = "Get user resource template by name and workspace service and optional version"

# cost report
API_GET_COSTS = "Get overall costs"
API_GET_WORKSPACE_COSTS = "Get workspace costs"
API_GET_COSTS_MAX_TIME_PERIOD = "The time period for pulling the data cannot exceed 1 year"
API_GET_COSTS_TO_DATE_NEED_TO_BE_LATER_THEN_FROM_DATE = "to_date needs to be later than from_date"
API_GET_COSTS_FROM_DATE_NEED_TO_BE_BEFORE_TO_DATE = "from_date needs to be before to_date"
API_GET_COSTS_SUBSCRIPTION_NOT_SUPPORTED = "Azure subscription doesn't support cost management"
API_GET_COSTS_TOO_MANY_REQUESTS = "Too many requests to Azure cost management API. Please retry."
API_GET_COSTS_SERVICE_UNAVAILABLE = "Azure cost management API is temporarily unavailable. Please retry."
API_GET_COSTS_INTERNAL_SERVER_ERROR = "Failed to query Azure TRE costs."


# State store status
OK = "OK"
NOT_OK = "Not OK"
COSMOS_DB = "Cosmos DB"
UNABLE_TO_GET_STATE_STORE_CLIENT = "Unable to get state store client"
STATE_STORE_ENDPOINT_NOT_RESPONDING = "State Store endpoint is not responding"
STATE_STORE_ENDPOINT_NOT_ACCESSIBLE = "State Store endpoint is not accessible"
UNSPECIFIED_ERROR = "Unspecified error"

# Service bus status
SERVICE_BUS = "Service Bus"
SERVICE_BUS_NOT_RESPONDING = "Service Bus is not responding"
SERVICE_BUS_AUTHENTICATION_ERROR = "Cannot authenticate Service Bus"

# Resource processor status
RESOURCE_PROCESSOR = "Resource Processor"
RESOURCE_PROCESSOR_GENERAL_ERROR_MESSAGE = "Resource Processor is not responding"
RESOURCE_PROCESSOR_HEALTHY_MESSAGE = "HealthState/healthy"

# Error strings
ACCESS_APP_IS_MISSING_ROLE = "The App is missing role"
ACCESS_PLEASE_SUPPLY_CLIENT_ID = "Please supply the client_id for the AAD application"
ACCESS_UNABLE_TO_GET_INFO_FOR_APP = "Unable to get app info for app:"
ACCESS_UNABLE_TO_GET_ROLE_ASSIGNMENTS_FOR_USER = "Unable to get role assignments for user"
ACCESS_UNABLE_TO_GET_ACCOUNT_TYPE = "Unable to look up account type"
ACCESS_UNHANDLED_ACCOUNT_TYPE = "Unhandled account type"

ACCESS_USER_IS_NOT_OWNER_OR_RESEARCHER = "Workspace Researcher or Owner rights are required"
ACCESS_USER_IS_NOT_OWNER = "Workspace Owner rights are required"
ACCESS_USER_DOES_NOT_HAVE_REQUIRED_ROLE = "The user is missing a required role"

AUTH_NOT_ASSIGNED_TO_ADMIN_ROLE = "Not assigned to admin role"
AUTH_COULD_NOT_VALIDATE_CREDENTIALS = "Could not validate credentials"
AUTH_CONFIGURATION_NOT_AVAILABLE_FOR_WORKSPACE = "Auth configuration not available for workspace"
AUTH_UNABLE_TO_VALIDATE_TOKEN = "Unable to decode or validate token"
INVALID_AUTH_PROVIDER = "Invalid authentication provider"
INVALID_SIGNATURE = "Invalid token signature"
EXPIRED_SIGNATURE = "Expired token signature"
INVALID_TOKEN = "Invalid token"

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
WORKSPACE_DOES_NOT_HAVE_ADDRESS_SPACES_PROPERTY = "Workspace does not have address_spaces property"
WORKSPACE_TEMPLATE_VERSION_EXISTS = "A template with this version already exists"
OPERATION_DOES_NOT_EXIST = "Operation does not exist"
CUSTOM_ACTION_NOT_DEFINED = "The specified custom action isn't defined in the targeted resource."
CUSTOM_ACTIONS_DO_NOT_EXIST = "The resource being targeted does not implement any custom actions."

WORKSPACE_SERVICE_TEMPLATE_DOES_NOT_EXIST = "Could not retrieve the workspace service template specified"
TEMPLATE_DOES_NOT_EXIST = "Could not retrieve the template with this name, or name-version pair"
NO_UNIQUE_CURRENT_FOR_TEMPLATE = "The template has multiple 'current' versions"

SHARED_SERVICE_DOES_NOT_EXIST = "Shared service does not exist"
SHARED_SERVICE_NEEDS_TO_BE_DISABLED_BEFORE_DELETION = "Shared service needs to be disabled before you can delete it"

SHARED_SERVICE_TEMPLATE_DOES_NOT_EXIST = "Could not retrieve the workspace service template specified"
SHARED_SERVICE_TEMPLATE_VERSION_EXISTS = "A template with this version already exists"

ETAG_CONFLICT = "This document has been modified by another user or process since you last retrieved it. Please get the document again and retry."
SWAGGER_DISABLED = "Swagger is disabled. Set 'ENABLE_SWAGGER' to true in order to access Swagger."

# Resource Status
RESOURCE_STATUS_AWAITING_DEPLOYMENT = "awaiting_deployment"
RESOURCE_STATUS_DEPLOYING = "deploying"
RESOURCE_STATUS_DEPLOYED = "deployed"
RESOURCE_STATUS_DEPLOYMENT_FAILED = "deployment_failed"

RESOURCE_STATUS_AWAITING_DELETION = "awaiting_deletion"
RESOURCE_STATUS_DELETING = "deleting"
RESOURCE_STATUS_DELETED = "deleted"
RESOURCE_STATUS_DELETING_FAILED = "deleting_failed"

RESOURCE_STATUS_AWAITING_UPDATE = "awaiting_update"
RESOURCE_STATUS_UPDATING = "updating"
RESOURCE_STATUS_UPDATED = "updated"
RESOURCE_STATUS_UPDATING_FAILED = "updating_failed"

# Resource Action
RESOURCE_ACTION_INSTALL = "install"
RESOURCE_ACTION_UPDATE = "upgrade"
RESOURCE_ACTION_UNINSTALL = "uninstall"


# Resource Action Status
RESOURCE_STATUS_AWAITING_ACTION = "awaiting_action"
RESOURCE_ACTION_STATUS_INVOKING = "invoking_action"
RESOURCE_ACTION_STATUS_SUCCEEDED = "action_succeeded"
RESOURCE_ACTION_STATUS_FAILED = "action_failed"

# Pipeline (multi-step) deployments
RESOURCE_ACTION_STATUS_PIPELINE_RUNNING = "pipeline_running"
RESOURCE_ACTION_STATUS_PIPELINE_FAILED = "pipeline_failed"
RESOURCE_ACTION_STATUS_PIPELINE_SUCCEEDED = "pipeline_succeeded"

# Resource Type
RESOURCE_TYPE_WORKSPACE = "workspace"
RESOURCE_TYPE_WORKSPACE_SERVICE = "workspace-service"
USER_RESOURCE = "user-resource"
RESOURCE_TYPE_SHARED_SERVICE = "shared-service"

# Airlock Resource Type
AIRLOCK_RESOURCE_TYPE_REQUEST = "airlock-request"
AIRLOCK_RESOURCE_TYPE_REVIEW = "airlock-review"

# Airlock Resource Status
AIRLOCK_RESOURCE_STATUS_DRAFT = "draft"
AIRLOCK_RESOURCE_STATUS_SUBMITTED = "submitted"
AIRLOCK_RESOURCE_STATUS_INREVIEW = "in_review"
AIRLOCK_RESOURCE_STATUS_APPROVAL_INPROGRESS = "approval_in_progress"
AIRLOCK_RESOURCE_STATUS_APPROVED = "approved"
AIRLOCK_RESOURCE_STATUS_REJECTION_INPROGRESS = "rejection_in_progress"
AIRLOCK_RESOURCE_STATUS_REJECTED = "rejected"
AIRLOCK_RESOURCE_STATUS_CANCELLED = "cancelled"
AIRLOCK_RESOURCE_STATUS_BLOCKING_INPROGRESS = "blocking_in_progress"
AIRLOCK_RESOURCE_STATUS_BLOCKED = "blocked_by_scan"
AIRLOCK_RESOURCE_STATUS_FAILED = "failed"
AIRLOCK_RESOURCE_STATUS_REVOKED = "revoked"

# Airlock Request Types
AIRLOCK_REQUEST_TYPE_IMPORT = "import"
AIRLOCK_REQUEST_TYPE_EXPORT = "export"

# Airlock Messages
AIRLOCK_REQUEST_DOES_NOT_EXIST = "Airlock request does not exist"
AIRLOCK_REQUEST_ILLEGAL_STATUS_CHANGE = "Airlock request status change was illegal"
AIRLOCK_REQUEST_IN_PROGRESS = "Airlock request is being processed, please try again later."
AIRLOCK_REQUEST_IS_CANCELED = "Airlock request was cancelled."
AIRLOCK_REQUEST_UNACCESSIBLE = "Airlock request is in invalid status: rejected, blocked or failed."
AIRLOCK_REQUEST_INVALID_STATUS = "Airlock request status is unknown."
AIRLOCK_UNAUTHORIZED_TO_SA = "User is unauthorized to access airlock request files in its current status."
AIRLOCK_NOT_ENABLED_IN_WORKSPACE = "Airlock is not enabled in this workspace."
AIRLOCK_NO_EMAIL = "There are no Workspace Researchers or Workspace Owners in the workspace with an email address."
AIRLOCK_NO_AIRLOCK_MANAGER_EMAIL = "There are no Airlock Managers in the workspace with an email address."

# Airlock Actions
AIRLOCK_ACTION_REVIEW = "review"
AIRLOCK_ACTION_CANCEL = "cancel"
AIRLOCK_ACTION_SUBMIT = "submit"
AIRLOCK_ACTION_REVOKE = "revoke"

# Airlock Review Decisions
AIRLOCK_REVIEW_DECISION_APPROVED = "approved"
AIRLOCK_REVIEW_DECISION_REJECTED = "rejected"
AIRLOCK_REVIEW_DECISION_REVOKED = "revoked"

# Deployments
RESOURCE_STATUS_AWAITING_DEPLOYMENT_MESSAGE = "This resource is waiting to be deployed"
RESOURCE_STATUS_AWAITING_UPDATE_MESSAGE = "This resource is waiting to be updated"
RESOURCE_STATUS_AWAITING_DELETION_MESSAGE = "This resource is waiting to be deleted"
RESOURCE_STATUS_AWAITING_ACTION_MESSAGE = "This resource is waiting for an action to be invoked"

# Service bus
SERVICE_BUS_GENERAL_ERROR_MESSAGE = "Service bus failure"
DEPLOYMENT_STATUS_MESSAGE_FORMAT_INCORRECT = "Service bus message is not formatted correctly"
DEPLOYMENT_STATUS_ID_NOT_FOUND = "Service bus message refers to resource id = {} which does not exist"
STEP_RESULT_MESSAGE_FORMAT_INCORRECT = "Service bus message of step result is not formatted correctly"
STEP_RESULT_ID_NOT_FOUND = "Service bus message of step result refers to resource id = {} which does not exist"
STEP_RESULT_MESSAGE_STATUS_DOES_NOT_MATCH = "Service bus message of step result current status does not match the one in state store for request id = {}, status in step result = {}, status in state store = {}"
STEP_RESULT_MESSAGE_INVALID_STATUS = "Service bus message has invalid status change request for request id = {}, current status is = {}, new status is = {}"

# Event grid
EVENT_GRID_GENERAL_ERROR_MESSAGE = "Event grid failure"

# Workspace creation validation
MISSING_REQUIRED_PARAMETERS = "Missing required parameters"
INVALID_EXTRA_PARAMETER = "Invalid extra parameters"
PARAMETERS_WITH_WRONG_TYPE = "Parameters with wrong type"

# Value that a sensitive is replaced with in Cosmos
REDACTED_SENSITIVE_VALUE = "REDACTED"

# User Management
USER_MANAGEMENT_DISABLED = "User management is disabled"

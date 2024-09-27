PONG = "pong"

API_HEALTH = "/api/health"
API_WORKSPACE_TEMPLATES = "/api/workspace-templates"
API_WORKSPACES = "/api/workspaces"
API_WORKSPACE_SERVICE_TEMPLATES = "/api/workspace-service-templates"
API_SHARED_SERVICE_TEMPLATES = "/api/shared-service-templates"
API_SHARED_SERVICES = "/api/shared-services"
API_WORKSPACE_SERVICES = "workspace-services"
API_USER_RESOURCES = "user-resources"

BASE_WORKSPACE = "tre-workspace-base"
UNRESTRICTED_WORKSPACE = "tre-workspace-unrestricted"
AIRLOCK_IMPORT_REVIEW_WORKSPACE = "tre-workspace-airlock-import-review"

AZUREML_SERVICE = "tre-service-azureml"
GUACAMOLE_SERVICE = "tre-service-guacamole"
GITEA_SERVICE = "tre-workspace-service-gitea"
MLFLOW_SERVICE = "tre-service-mlflow"
MYSQL_SERVICE = "tre-workspace-service-mysql"
HEALTH_SERVICE = "tre-workspace-service-health"
AZURESQL_SERVICE = "tre-workspace-service-azuresql"
OPENAI_SERVICE = "tre-workspace-service-openai"

FIREWALL_SHARED_SERVICE = "tre-shared-service-firewall"
GITEA_SHARED_SERVICE = "tre-shared-service-gitea"
NEXUS_SHARED_SERVICE = "tre-shared-service-sonatype-nexus"
AIRLOCK_NOTIFIER_SHARED_SERVICE = "tre-shared-service-airlock-notifier"
CERTS_SHARED_SERVICE = "tre-shared-service-certs"
ADMIN_VM_SHARED_SERVICE = "tre-shared-service-admin-vm"
CYCLECLOUD_SHARED_SERVICE = "tre-shared-service-cyclecloud"

GUACAMOLE_WINDOWS_USER_RESOURCE = "tre-service-guacamole-windowsvm"
GUACAMOLE_LINUX_USER_RESOURCE = "tre-service-guacamole-linuxvm"

TEST_WORKSPACE_SERVICE_TEMPLATE = "e2e-test-workspace-service"

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

# Resource Action Status
RESOURCE_STATUS_AWAITING_ACTION = "awaiting_action"
RESOURCE_ACTION_STATUS_INVOKING = "invoking_action"
RESOURCE_ACTION_STATUS_SUCCEEDED = "action_succeeded"
RESOURCE_ACTION_STATUS_FAILED = "action_failed"

# Pipeline (multi-step) deployments
RESOURCE_ACTION_STATUS_PIPELINE_RUNNING = "pipeline_running"
RESOURCE_ACTION_STATUS_PIPELINE_FAILED = "pipeline_failed"
RESOURCE_ACTION_STATUS_PIPELINE_SUCCEEDED = "pipeline_succeeded"

import uuid
from typing import List

from azure.cosmos import CosmosClient
from pydantic import parse_obj_as, UUID4

from core import config
from resources import strings
from db.errors import EntityDoesNotExist, WorkspaceValidationError
from models.domain.workspace import Workspace
from db.repositories.base import BaseRepository
from models.domain.resource import Deployment, Status
from models.domain.resource_template import ResourceTemplate, Parameter
from models.schemas.workspace import WorkspaceInCreate
from db.repositories.workspace_templates import WorkspaceTemplateRepository


class WorkspaceRepository(BaseRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client, config.STATE_STORE_RESOURCES_CONTAINER)

    @staticmethod
    def _active_workspaces_query():
        return 'SELECT * FROM c WHERE c.resourceType = "workspace" AND c.isDeleted = false'

    def _get_current_workspace_template(self, template_name) -> ResourceTemplate:
        workspace_template_repo = WorkspaceTemplateRepository(self._client)
        template = workspace_template_repo.get_current_workspace_template_by_name(template_name)
        return template

    @staticmethod
    def _convert_type_name(s: str) -> str:
        if s == 'str':
            return 'string'
        if s == 'int':
            return 'integer'
        return 'invalid'

    @staticmethod
    def _system_provided_parameters() -> List[str]:
        return ["acr_name",
                "porter_driver",
                "tfstate_container_name",
                "tfstate_resource_group_name",
                "tfstate_storage_account_name"]

    @staticmethod
    def _check_that_all_required_parameters_exist(template_parameters: List[Parameter], supplied_request_parameters: dict, errors: dict):
        missing_required = []
        system_provided = WorkspaceRepository._system_provided_parameters()
        required_parameters = [parameter for parameter in template_parameters if parameter.required and parameter.name not in system_provided]
        missing_required = [parameter.name for parameter in required_parameters if parameter.name not in supplied_request_parameters]

        if missing_required:
            errors[strings.MISSING_REQUIRED_PARAMETERS] = missing_required

        pass

    @staticmethod
    def _validate_given_parameters(template_parameters: List[Parameter], supplied_request_parameters: dict, errors: dict):
        extra_parameters = []
        wrong_type = []
        template_parameters_by_name = {parameter.name: parameter for parameter in template_parameters}
        for parameter in supplied_request_parameters:
            if parameter not in template_parameters_by_name:
                extra_parameters.append(parameter)
            else:
                template_parameter = template_parameters_by_name[parameter]
                supplied_parameter_type = WorkspaceRepository._convert_type_name(type(supplied_request_parameters[parameter]).__name__)
                if supplied_parameter_type != template_parameter.type:
                    wrong_type.append({"parameter": parameter, "expected_type": template_parameter.type, "supplied_type": supplied_parameter_type})

        if extra_parameters:
            errors[strings.INVALID_EXTRA_PARAMETER] = extra_parameters

        if wrong_type:
            errors[strings.PARAMETERS_WITH_WRONG_TYPE] = wrong_type

        pass

    @staticmethod
    def _validate_workspace_parameters(template_parameters: List[Parameter], supplied_request_parameters: dict):
        errors = {}

        WorkspaceRepository._check_that_all_required_parameters_exist(template_parameters, supplied_request_parameters, errors)

        WorkspaceRepository._validate_given_parameters(template_parameters, supplied_request_parameters, errors)

        if errors:
            raise WorkspaceValidationError(errors)

        pass

    def get_all_active_workspaces(self) -> List[Workspace]:
        query = self._active_workspaces_query()
        workspaces = self.query(query=query)
        return parse_obj_as(List[Workspace], workspaces)

    def get_workspace_by_workspace_id(self, workspace_id: UUID4) -> Workspace:
        query = self._active_workspaces_query() + f' AND c.id="{workspace_id}"'
        workspaces = self.query(query=query)
        if not workspaces:
            raise EntityDoesNotExist
        return parse_obj_as(Workspace, workspaces[0])

    def create_workspace_item(self, workspace_create: WorkspaceInCreate, auth_info: dict) -> Workspace:
        full_workspace_id = str(uuid.uuid4())

        try:
            current_template = self._get_current_workspace_template(workspace_create.workspaceType)
            template_version = current_template.version
        except EntityDoesNotExist:
            raise ValueError(f"The workspace type '{workspace_create.workspaceType}' does not exist")

        # system generated parameters
        resource_spec_parameters = {
            "azure_location": config.RESOURCE_LOCATION,
            "workspace_id": full_workspace_id[-4:],
            "tre_id": config.TRE_ID,
            "address_space": "10.2.1.0/24"  # TODO: Calculate this value - Issue #52
        }

        # user provided parameters
        for parameter in workspace_create.parameters:
            resource_spec_parameters[parameter] = workspace_create.parameters[parameter]

        workspace = Workspace(
            id=full_workspace_id,
            displayName=workspace_create.displayName,
            description=workspace_create.description,
            resourceTemplateName=workspace_create.workspaceType,
            resourceTemplateVersion=template_version,
            resourceTemplateParameters=resource_spec_parameters,
            deployment=Deployment(status=Status.NotDeployed, message=strings.RESOURCE_STATUS_NOT_DEPLOYED_MESSAGE),
            authInformation=auth_info
        )

        self._validate_workspace_parameters(current_template.parameters, workspace.resourceTemplateParameters)

        return workspace

    def save_workspace(self, workspace: Workspace):
        self.create_item(workspace)

    def update_workspace(self, workspace: Workspace):
        self.container.upsert_item(body=workspace.dict())

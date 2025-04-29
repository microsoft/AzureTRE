import uuid
from typing import List, Tuple
from azure.mgmt.storage import StorageManagementClient
from pydantic import parse_obj_as
from db.repositories.resources_history import ResourceHistoryRepository
from models.domain.resource_template import ResourceTemplate
from models.domain.authentication import User

import resources.strings as strings
from core import config, credentials
from db.errors import EntityDoesNotExist, InvalidInput, ResourceIsNotDeployed
from db.repositories.resource_templates import ResourceTemplateRepository
from db.repositories.resources import ResourceRepository, IS_NOT_DELETED_CLAUSE
from db.repositories.operations import OperationRepository
from models.domain.resource import ResourceType
from models.domain.workspace import Workspace
from models.schemas.resource import ResourcePatch
from models.schemas.workspace import WorkspaceInCreate
from services.cidr_service import generate_new_cidr, is_network_available


class WorkspaceRepository(ResourceRepository):
    """
    Repository class representing data storage for Workspaces
    """

    # We allow the users some predefined TShirt sizes for the address space
    predefined_address_spaces = {"small": 24, "medium": 22, "large": 16}

    @classmethod
    async def create(cls):
        cls = WorkspaceRepository()
        await super().create()
        return cls

    @staticmethod
    def workspaces_query_string():
        return f'SELECT * FROM c WHERE c.resourceType = "{ResourceType.Workspace}"'

    @staticmethod
    def active_workspaces_query_string():
        return f'SELECT * FROM c WHERE c.resourceType = "{ResourceType.Workspace}" AND {IS_NOT_DELETED_CLAUSE}'

    async def get_workspaces(self) -> List[Workspace]:
        query = WorkspaceRepository.workspaces_query_string()
        workspaces = await self.query(query=query)
        return parse_obj_as(List[Workspace], workspaces)

    async def get_active_workspaces(self) -> List[Workspace]:
        query = WorkspaceRepository.active_workspaces_query_string()
        workspaces = await self.query(query=query)
        return parse_obj_as(List[Workspace], workspaces)

    async def get_deployed_workspace_by_id(self, workspace_id: str, operations_repo: OperationRepository) -> Workspace:
        workspace = await self.get_workspace_by_id(workspace_id)

        if (not await operations_repo.resource_has_deployed_operation(resource_id=workspace_id)):
            raise ResourceIsNotDeployed

        return workspace

    async def get_workspace_by_id(self, workspace_id: str) -> Workspace:
        query = self.workspaces_query_string() + f' AND c.id = "{workspace_id}"'
        workspaces = await self.query(query=query)
        if not workspaces:
            raise EntityDoesNotExist
        return parse_obj_as(Workspace, workspaces[0])

    # Remove this method once not using last 4 digits for naming - https://github.com/microsoft/AzureTRE/issues/3666
    async def is_workspace_storage_account_available(self, workspace_id: str) -> bool:
        storage_client = StorageManagementClient(credentials.get_credential(), config.SUBSCRIPTION_ID)
        # check for storage account with last 4 digits of workspace_id
        availability_result = storage_client.storage_accounts.check_name_availability(
            {
                "name": f"stgws{workspace_id[-4:]}"
            }
        )
        return availability_result.name_available

    async def create_workspace_item(self, workspace_input: WorkspaceInCreate, auth_info: dict, workspace_owner_object_id: str, user_roles: List[str]) -> Tuple[Workspace, ResourceTemplate]:

        full_workspace_id = str(uuid.uuid4())

        # Ensure workspace with last four digits of ID does not already exist - remove when https://github.com/microsoft/AzureTRE/issues/3666 is resolved
        while not await self.is_workspace_storage_account_available(full_workspace_id):
            full_workspace_id = str(uuid.uuid4())

        template = await self.validate_input_against_template(workspace_input.templateName, workspace_input, ResourceType.Workspace, user_roles)

        # allow for workspace template taking a single address_space or multiple address_spaces
        intial_address_space = await self.get_address_space_based_on_size(workspace_input.properties)
        address_space_param = {"address_space": intial_address_space}
        address_spaces_param = {"address_spaces": [intial_address_space]}

        auto_app_registration_param = {"register_aad_application": self.automatically_create_application_registration(workspace_input.properties)}
        workspace_owner_param = {"workspace_owner_object_id": self.get_workspace_owner(workspace_input.properties, workspace_owner_object_id)}

        # we don't want something in the input to overwrite the system parameters,
        # so dict.update can't work. Priorities from right to left.
        resource_spec_parameters = {**workspace_input.properties,
                                    **address_space_param,
                                    **address_spaces_param,
                                    **auto_app_registration_param,
                                    **workspace_owner_param,
                                    **auth_info,
                                    **self.get_workspace_spec_params(full_workspace_id)}

        workspace = Workspace(
            id=full_workspace_id,
            templateName=workspace_input.templateName,
            templateVersion=template.version,
            properties=resource_spec_parameters,
            resourcePath=f'/workspaces/{full_workspace_id}',
            etag=''  # need to validate the model
        )

        return workspace, template

    def get_workspace_owner(self, workspace_properties: dict, workspace_owner_object_id: str) -> str:
        # Add the objectId of the user that will become the workspace owner. If it is not present in
        # the request, we can assume the logged in user will be WorkspaceOwner
        user_defined_workspace_owner_object_id = workspace_properties.get("workspace_owner_object_id")
        return workspace_owner_object_id if user_defined_workspace_owner_object_id is None else user_defined_workspace_owner_object_id

    def automatically_create_application_registration(self, workspace_properties: dict) -> bool:
        return True if ("auth_type" in workspace_properties and workspace_properties["auth_type"] == "Automatic") else False

    async def get_address_space_based_on_size(self, workspace_properties: dict):
        # Default the address space to 'small' if not supplied.
        address_space_size = workspace_properties.get("address_space_size", "small").lower()

        # 773 allow custom sized networks to be requested
        if (address_space_size == "custom"):
            if (await self.validate_address_space(workspace_properties.get("address_space"))):
                return workspace_properties.get("address_space")
            else:
                raise InvalidInput("The custom 'address_space' you requested does not fit in the current network.")

        # Default mask is 24 (small)
        cidr_netmask = WorkspaceRepository.predefined_address_spaces.get(address_space_size, 24)
        return await self.get_new_address_space(cidr_netmask)

    # 772 check that the provided address_space is available in the network.
    async def validate_address_space(self, address_space):
        if (address_space is None):
            raise InvalidInput("Missing 'address_space' from properties.")

        allocated_networks = [x.properties["address_space"] for x in await self.get_active_workspaces()]
        return is_network_available(allocated_networks, address_space)

    async def get_new_address_space(self, cidr_netmask: int = 24):
        workspaces = await self.get_active_workspaces()
        networks = [[x.properties.get("address_space")] for x in workspaces]
        networks = networks + [x.properties.get("address_spaces", []) for x in workspaces]
        networks = [i for s in networks for i in s if i is not None]

        new_address_space = generate_new_cidr(networks, cidr_netmask)
        return new_address_space

    async def patch_workspace(self, workspace: Workspace, workspace_patch: ResourcePatch, etag: str, resource_template_repo: ResourceTemplateRepository, resource_history_repo: ResourceHistoryRepository, user: User, force_version_update: bool) -> Tuple[Workspace, ResourceTemplate]:
        # get the workspace template
        workspace_template = await resource_template_repo.get_template_by_name_and_version(workspace.templateName, workspace.templateVersion, ResourceType.Workspace)
        return await self.patch_resource(workspace, workspace_patch, workspace_template, etag, resource_template_repo, resource_history_repo, user, strings.RESOURCE_ACTION_UPDATE, force_version_update)

    def get_workspace_spec_params(self, full_workspace_id: str):
        params = self.get_resource_base_spec_params()
        params.update({
            "azure_location": config.RESOURCE_LOCATION,
            "workspace_id": full_workspace_id[-4:],  # TODO: remove with #729
        })
        return params

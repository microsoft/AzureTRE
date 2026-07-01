import uuid
from typing import List, Tuple
import asyncio
from azure.mgmt.storage.aio import StorageManagementClient

from pydantic import parse_obj_as
from db.repositories.resources_history import ResourceHistoryRepository
from models.domain.resource_template import ResourceTemplate
from models.domain.authentication import User

import resources.strings as strings
from core import config, credentials
from db.errors import EntityDoesNotExist, InvalidInput, ResourceIsNotDeployed
from db.repositories.resource_templates import ResourceTemplateRepository
from db.repositories.resources import ResourceRepository
from models.domain.operation import Status
from db.repositories.operations import OperationRepository
from models.domain.resource import ResourceType
from models.domain.workspace import Workspace
from models.schemas.resource import ResourcePatch
from models.schemas.workspace import WorkspaceInCreate
from services.cidr_service import generate_new_cidr, is_network_available
from services.logging import logger


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
        query = 'SELECT * FROM c WHERE c.resourceType = @resourceType'
        parameters = [
            {'name': '@resourceType', 'value': ResourceType.Workspace}
        ]
        return query, parameters

    @staticmethod
    def active_workspaces_query_string():
        query = 'SELECT * FROM c WHERE c.resourceType = @resourceType AND c.deploymentStatus != @deletedStatus'
        parameters = [
            {'name': '@resourceType', 'value': ResourceType.Workspace},
            {'name': '@deletedStatus', 'value': Status.Deleted}
        ]
        return query, parameters

    async def get_workspaces(self) -> List[Workspace]:
        query, parameters = WorkspaceRepository.workspaces_query_string()
        workspaces = await self.query(query=query, parameters=parameters)
        return parse_obj_as(List[Workspace], workspaces)

    async def get_active_workspaces(self) -> List[Workspace]:
        query, parameters = WorkspaceRepository.active_workspaces_query_string()
        workspaces = await self.query(query=query, parameters=parameters)
        return parse_obj_as(List[Workspace], workspaces)

    async def get_deployed_workspace_by_id(self, workspace_id: str, operations_repo: OperationRepository) -> Workspace:
        workspace = await self.get_workspace_by_id(workspace_id)

        if (not await operations_repo.resource_has_deployed_operation(resource_id=workspace_id)):
            raise ResourceIsNotDeployed

        return workspace

    async def get_workspace_by_id(self, workspace_id: str) -> Workspace:
        query, parameters = self.workspaces_query_string()
        query += ' AND c.id = @workspaceId AND c.deploymentStatus != @deletedStatus'
        parameters.append({'name': '@workspaceId', 'value': str(workspace_id)})
        parameters.append({'name': '@deletedStatus', 'value': Status.Deleted})
        workspaces = await self.query(query=query, parameters=parameters)
        if not workspaces:
            raise EntityDoesNotExist
        return parse_obj_as(Workspace, workspaces[0])

    _NAME_CHECK_TIMEOUT_SECONDS = 5.0
    _NAME_CHECK_MAX_ATTEMPTS = 3

    def _create_storage_client(self, credential) -> StorageManagementClient:
        return StorageManagementClient(
            credential,
            config.SUBSCRIPTION_ID,
            base_url=config.RESOURCE_MANAGER_ENDPOINT,
            credential_scopes=config.CREDENTIAL_SCOPES,
        )

    # Remove this method once not using last 4 digits for naming - https://github.com/microsoft/AzureTRE/issues/3666
    async def is_workspace_storage_account_available(self, credential, workspace_id: str) -> bool:
        suffix = workspace_id[-4:]
        # Checking only the primary storage account name is sufficient because all storage accounts
        # share the same random 4-digit suffix. A collision on other names without a collision
        # on the primary name is practically impossible (1 in 65,536 chance globally).
        # This reduces API calls by 83% and avoids Storage RP rate-limiting/tarpitting.
        names_to_check = [
            f"stgws{suffix}"
        ]
        storage_client = self._create_storage_client(credential)
        try:
            for name in names_to_check:
                logger.info("Checking storage account name availability: %s", name)
                for attempt in range(1, self._NAME_CHECK_MAX_ATTEMPTS + 1):
                    try:
                        result = await asyncio.wait_for(
                            storage_client.storage_accounts.check_name_availability({"name": name}),
                            timeout=self._NAME_CHECK_TIMEOUT_SECONDS,
                        )
                        if not result.name_available:
                            logger.info("Storage account name is not available: %s", name)
                            return False
                        break  # available - move to the next name
                    except (asyncio.TimeoutError, Exception) as e:
                        status_code = getattr(e, "status_code", None)
                        err_details = f"HTTP {status_code}: {e}" if status_code else f"{type(e).__name__} ({e})"
                        # A stalled call is almost always a poisoned keep-alive connection or rate limit.
                        # Drop this client (and its connection pool) and retry on a fresh one.
                        logger.warning(
                            "Storage name availability check timed out or failed for %s (attempt %d/%d): %s; "
                            "recreating storage client",
                            name, attempt, self._NAME_CHECK_MAX_ATTEMPTS, err_details,
                        )
                        await storage_client.close()
                        storage_client = self._create_storage_client(credential)
                else:
                    logger.warning(
                        "Storage name availability check persistently timed out or failed for %s after %d attempts. "
                        "Assuming name is available to prevent blocking workspace creation.",
                        name, self._NAME_CHECK_MAX_ATTEMPTS,
                    )
            return True
        finally:
            await storage_client.close()

    async def create_workspace_item(self, workspace_input: WorkspaceInCreate, auth_info: dict, workspace_owner_object_id: str, user_roles: List[str]) -> Tuple[Workspace, ResourceTemplate]:

        full_workspace_id = str(uuid.uuid4())

        # Ensure workspace with last four digits of ID does not already exist - remove when https://github.com/microsoft/AzureTRE/issues/3666 is resolved
        attempts = 0
        max_attempts = 5
        async with credentials.get_credential_async_context() as credential:
            while not await self.is_workspace_storage_account_available(credential, full_workspace_id):
                attempts += 1
                if attempts >= max_attempts:
                    # If we exceed the maximum attempts, raise a ValueError to prevent hitting App Gateway timeout
                    raise ValueError("Unable to generate a unique storage account name after multiple attempts.")
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

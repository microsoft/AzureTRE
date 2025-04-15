from sqlite3 import InternalError
from typing import List, Tuple
import uuid

from pydantic import parse_obj_as
import resources.strings as strings
from models.domain.resource_template import ResourceTemplate
from models.domain.authentication import User
from db.repositories.resource_templates import ResourceTemplateRepository
from db.repositories.resources_history import ResourceHistoryRepository
from db.repositories.resources import ResourceRepository, IS_NOT_DELETED_CLAUSE, IS_ACTIVE_RESOURCE
from db.errors import DuplicateEntity, EntityDoesNotExist
from models.domain.shared_service import SharedService
from models.schemas.resource import ResourcePatch
from models.schemas.shared_service_template import SharedServiceTemplateInCreate
from models.domain.resource import ResourceType


class SharedServiceRepository(ResourceRepository):
    @classmethod
    async def create(cls):
        cls = SharedServiceRepository()
        await super().create()
        return cls

    @staticmethod
    def shared_service_query(shared_service_id: str):
        return f'SELECT * FROM c WHERE c.resourceType = "{ResourceType.SharedService}" AND c.id = "{shared_service_id}"'

    @staticmethod
    def active_shared_services_query():
        return f'SELECT * FROM c WHERE {IS_NOT_DELETED_CLAUSE} AND c.resourceType = "{ResourceType.SharedService}"'

    @staticmethod
    def active_shared_service_with_template_name_query(template_name: str):
        return f'SELECT * FROM c WHERE {IS_ACTIVE_RESOURCE} AND c.resourceType = "{ResourceType.SharedService}" AND c.templateName = "{template_name}"'

    async def get_shared_service_by_id(self, shared_service_id: str):
        shared_services = await self.query(self.shared_service_query(shared_service_id))
        if not shared_services:
            raise EntityDoesNotExist
        return parse_obj_as(SharedService, shared_services[0])

    async def get_active_shared_services(self) -> List[SharedService]:
        """
        returns list of "non-deleted" shared services linked to this shared
        """
        query = SharedServiceRepository.active_shared_services_query()
        shared_services = await self.query(query=query)
        return parse_obj_as(List[SharedService], shared_services)

    def get_shared_service_spec_params(self):
        return self.get_resource_base_spec_params()

    async def create_shared_service_item(self, shared_service_input: SharedServiceTemplateInCreate, user_roles: List[str]) -> Tuple[SharedService, ResourceTemplate]:
        shared_service_id = str(uuid.uuid4())

        existing_shared_services = await self.query(self.active_shared_service_with_template_name_query(shared_service_input.templateName))

        # Duplicate is same template (=id), same version and deployed
        if existing_shared_services:
            if len(existing_shared_services) > 1:
                raise InternalError(f"More than one active shared service exists with the same id {shared_service_id}")
            raise DuplicateEntity

        template = await self.validate_input_against_template(shared_service_input.templateName, shared_service_input, ResourceType.SharedService, user_roles)

        resource_spec_parameters = {**shared_service_input.properties, **self.get_shared_service_spec_params()}

        shared_service = SharedService(
            id=shared_service_id,
            templateName=shared_service_input.templateName,
            templateVersion=template.version,
            properties=resource_spec_parameters,
            resourcePath=f'/shared-services/{shared_service_id}',
            etag=''
        )

        return shared_service, template

    async def patch_shared_service(self, shared_service: SharedService, shared_service_patch: ResourcePatch, etag: str, resource_template_repo: ResourceTemplateRepository, resource_history_repo: ResourceHistoryRepository, user: User, force_version_update: bool) -> Tuple[SharedService, ResourceTemplate]:
        # get shared service template
        shared_service_template = await resource_template_repo.get_template_by_name_and_version(shared_service.templateName, shared_service.templateVersion, ResourceType.SharedService)
        return await self.patch_resource(shared_service, shared_service_patch, shared_service_template, etag, resource_template_repo, resource_history_repo, user, strings.RESOURCE_ACTION_UPDATE, force_version_update)

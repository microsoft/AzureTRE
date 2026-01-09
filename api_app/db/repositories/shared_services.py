from sqlite3 import InternalError
from typing import List, Tuple
import uuid

from pydantic import parse_obj_as
import resources.strings as strings
from models.domain.resource_template import ResourceTemplate
from models.domain.authentication import User
from db.repositories.resource_templates import ResourceTemplateRepository
from db.repositories.resources_history import ResourceHistoryRepository
from db.repositories.resources import ResourceRepository
from db.errors import DuplicateEntity, EntityDoesNotExist
from models.domain.shared_service import SharedService
from models.schemas.resource import ResourcePatch
from models.schemas.shared_service_template import SharedServiceTemplateInCreate
from models.domain.resource import ResourceType
from models.domain.operation import Status


class SharedServiceRepository(ResourceRepository):
    @classmethod
    async def create(cls):
        cls = SharedServiceRepository()
        await super().create()
        return cls

    @staticmethod
    def shared_service_query(shared_service_id: str):
        query = 'SELECT * FROM c WHERE c.resourceType = @resourceType AND c.id = @sharedServiceId'
        parameters = [
            {'name': '@resourceType', 'value': ResourceType.SharedService},
            {'name': '@sharedServiceId', 'value': shared_service_id}
        ]
        return query, parameters

    @staticmethod
    def active_shared_services_query():
        query = 'SELECT * FROM c WHERE c.deploymentStatus != @deletedStatus AND c.resourceType = @resourceType'
        parameters = [
            {'name': '@deletedStatus', 'value': Status.Deleted},
            {'name': '@resourceType', 'value': ResourceType.SharedService}
        ]
        return query, parameters

    @staticmethod
    def active_shared_service_with_template_name_query(template_name: str):
        query = 'SELECT * FROM c WHERE c.deploymentStatus != @deletedStatus AND c.deploymentStatus != @failedStatus AND c.resourceType = @resourceType AND c.templateName = @templateName'
        parameters = [
            {'name': '@deletedStatus', 'value': Status.Deleted},
            {'name': '@failedStatus', 'value': Status.DeploymentFailed},
            {'name': '@resourceType', 'value': ResourceType.SharedService},
            {'name': '@templateName', 'value': template_name}
        ]
        return query, parameters

    async def get_shared_service_by_id(self, shared_service_id: str):
        query, parameters = self.shared_service_query(str(shared_service_id))
        query += ' AND c.deploymentStatus != @deletedStatus'
        parameters.append({'name': '@deletedStatus', 'value': Status.Deleted})
        shared_services = await self.query(query=query, parameters=parameters)
        if not shared_services:
            raise EntityDoesNotExist
        return parse_obj_as(SharedService, shared_services[0])

    async def get_active_shared_services(self) -> List[SharedService]:
        """
        returns list of "non-deleted" shared services linked to this shared
        """
        query, parameters = SharedServiceRepository.active_shared_services_query()
        shared_services = await self.query(query=query, parameters=parameters)
        return parse_obj_as(List[SharedService], shared_services)

    def get_shared_service_spec_params(self):
        return self.get_resource_base_spec_params()

    async def create_shared_service_item(self, shared_service_input: SharedServiceTemplateInCreate, user_roles: List[str]) -> Tuple[SharedService, ResourceTemplate]:
        shared_service_id = str(uuid.uuid4())

        query, parameters = self.active_shared_service_with_template_name_query(shared_service_input.templateName)
        existing_shared_services = await self.query(query=query, parameters=parameters)

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

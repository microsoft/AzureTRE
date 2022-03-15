import uuid
from typing import List

from azure.cosmos import CosmosClient
from pydantic import parse_obj_as
from db.repositories.resource_templates import ResourceTemplateRepository
from db.repositories.resources import ResourceRepository, IS_ACTIVE_CLAUSE
from db.repositories.operations import OperationRepository
from db.errors import ResourceIsNotDeployed, EntityDoesNotExist
from models.domain.shared_service import SharedService
from models.schemas.resource import ResourcePatch
from models.schemas.shared_service_template import SharedServiceTemplateInCreate
from models.domain.resource import ResourceType


class SharedServiceRepository(ResourceRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)

    @staticmethod
    def shared_service_query(shared_service_id: str):
        return f'SELECT * FROM c WHERE c.resourceType = "{ResourceType.SharedService}" AND c.id = "{shared_service_id}"'

    @staticmethod
    def active_shared_services_query():
        return f'SELECT * FROM c WHERE {IS_ACTIVE_CLAUSE} AND c.resourceType = "{ResourceType.SharedService}"'

    def get_shared_service_by_id(self, shared_service_id: str):
        shared_services = self.query(self.shared_service_query(shared_service_id))
        if not shared_services:
            raise EntityDoesNotExist
        return parse_obj_as(SharedService, shared_services[0])

    def get_active_shared_services(self) -> List[SharedService]:
        """
        returns list of "non-deleted" shared services linked to this shared
        """
        query = SharedServiceRepository.active_shared_services_query()
        shared_services = self.query(query=query)
        return parse_obj_as(List[SharedService], shared_services)

    def get_deployed_shared_service_by_id(self, shared_service_id: str, operations_repo: OperationRepository):
        shared_service = self.get_shared_service_by_id(shared_service_id)

        if (not operations_repo.resource_has_deployed_operation(resource_id=shared_service_id)):
            raise ResourceIsNotDeployed

        return shared_service

    def get_shared_service_spec_params(self):
        return self.get_resource_base_spec_params()

    def create_shared_service_item(self, shared_service_input: SharedServiceTemplateInCreate) -> SharedService:
        shared_service_id = str(uuid.uuid4())
        template_version = self.validate_input_against_template(shared_service_input.templateName, shared_service_input, ResourceType.SharedService)

        resource_spec_parameters = {**shared_service_input.properties, **self.get_shared_service_spec_params()}

        shared_service = SharedService(
            id=shared_service_id,
            templateName=shared_service_input.templateName,
            templateVersion=template_version,
            properties=resource_spec_parameters,
            resourcePath=f'/shared-services/{shared_service_id}',
            etag=''
        )

        return shared_service

    def patch_shared_service(self, shared_service: SharedService, shared_service_patch: ResourcePatch, etag: str, resource_template_repo: ResourceTemplateRepository) -> SharedService:
        # get shared service template
        shared_service_template = resource_template_repo.get_template_by_name_and_version(shared_service.templateName, shared_service.templateVersion, ResourceType.SharedService)
        return self.patch_resource(shared_service, shared_service_patch, shared_service_template, etag, resource_template_repo)

from db.errors import EntityDoesNotExist, EntityVersionExist
from db.repositories.resource_templates import ResourceTemplateRepository
from models.domain.resource_template import ResourceTemplate
from models.domain.resource import ResourceType
from models.schemas.resource_template import ResourceTemplateInCreate
from models.schemas.user_resource_template import UserResourceTemplateInCreate


def create_template_by_resource_type(template_input: ResourceTemplateInCreate, template_repo: ResourceTemplateRepository, resource_type: ResourceType) -> ResourceTemplate:
    try:
        template = template_repo.get_template_by_name_and_version(template_input.name, template_input.version, resource_type)
        if template:
            raise EntityVersionExist
    except EntityDoesNotExist:
        try:
            template = template_repo.get_current_template(template_input.name, resource_type)
            if template_input.current:
                template.current = False
                template_repo.update_item(template)
        except EntityDoesNotExist:
            # first registration
            template_input.current = True  # For first time registration, template is always marked current
        return template_repo.create_template(template_input, resource_type)


def create_user_resource_template(template_input: UserResourceTemplateInCreate, template_repo: ResourceTemplateRepository, workspace_service_template_name: str) -> ResourceTemplate:
    try:
        template = template_repo.get_template_by_name_and_version(template_input.name, template_input.version, ResourceType.UserResource)
        if template:
            raise EntityVersionExist
    except EntityDoesNotExist:
        try:
            template = template_repo.get_current_template(template_input.name, ResourceType.UserResource)
            if template_input.current:
                template.current = False
                template_repo.update_item(template)
        except EntityDoesNotExist:
            # first registration
            template_input.current = True  # For first time registration, template is always marked current
        return template_repo.create_template(template_input, ResourceType.UserResource, workspace_service_template_name)

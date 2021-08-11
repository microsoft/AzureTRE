from db.errors import EntityDoesNotExist, EntityVersionExist
from db.repositories.resource_templates import ResourceTemplateRepository
from db.repositories.user_resource_templates import UserResourceTemplateRepository
from models.domain.resource_template import ResourceTemplate
from models.domain.resource import ResourceType
from models.domain.user_resource_template import UserResourceTemplate
from models.schemas.resource_template import ResourceTemplateInCreate
from models.schemas.user_resource_template import UserResourceTemplateInCreate


def create_template_by_resource_type(resource_template_create: ResourceTemplateInCreate,
                                     resource_template_repo: ResourceTemplateRepository,
                                     resource_type: ResourceType) -> ResourceTemplate:
    try:
        template = resource_template_repo.get_resource_template_by_name_and_version(resource_template_create.name,
                                                                                    resource_template_create.version,
                                                                                    resource_type)
        if template:
            raise EntityVersionExist
    except EntityDoesNotExist:
        try:
            template = resource_template_repo.get_current_resource_template_by_name(resource_template_create.name,
                                                                                    resource_type)
            if resource_template_create.current:
                template.current = False
                resource_template_repo.update_item(template)
        except EntityDoesNotExist:
            # first registration
            resource_template_create.current = True  # For first time registration, template is always marked current
        return resource_template_repo.create_resource_template_item(resource_template_create, resource_type)


def create_user_resource_template(user_resource_template_create: UserResourceTemplateInCreate,
                                  user_resource_template_repo: UserResourceTemplateRepository,
                                  workspace_service_template_name: str) -> UserResourceTemplate:
    try:
        template = user_resource_template_repo.get_resource_template_by_name_and_version(
            user_resource_template_create.name,
            user_resource_template_create.version,
            ResourceType.UserResource)
        print(template)
        if template:
            raise EntityVersionExist
    except EntityDoesNotExist:
        try:
            template = user_resource_template_repo.get_current_resource_template_by_name(
                user_resource_template_create.name,
                ResourceType.UserResource)
            if user_resource_template_create.current:
                template.current = False
                user_resource_template_repo.update_item(template)
        except EntityDoesNotExist:
            # first registration
            user_resource_template_create.current = True  # For first time registration, template is always marked current
        return user_resource_template_repo.create_user_resource_template_item(user_resource_template_create, workspace_service_template_name)

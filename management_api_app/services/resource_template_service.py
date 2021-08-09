from db.errors import EntityDoesNotExist, EntityVersionExist
from db.repositories.resource_templates import ResourceTemplateRepository
from models.domain.resource_template import ResourceTemplate
from models.domain.resource import ResourceType
from models.schemas.template import TemplateInCreate


def create_template_by_resource_type(workspace_template_create: TemplateInCreate,
                                     workspace_template_repo: ResourceTemplateRepository,
                                     resource_type: ResourceType) -> ResourceTemplate:
    try:
        template = workspace_template_repo.get_workspace_template_by_name_and_version(workspace_template_create.name,
                                                                                      workspace_template_create.version)
        if template:
            raise EntityVersionExist
    except EntityDoesNotExist:
        try:
            template = workspace_template_repo.get_current_resource_template_by_name(workspace_template_create.name)
            if workspace_template_create.current:
                template.current = False
                workspace_template_repo.update_item(template)
        except EntityDoesNotExist:
            # first registration
            workspace_template_create.current = True  # For first time registration, template is always marked current
        return workspace_template_repo.create_resource_template_item(workspace_template_create, resource_type)
from starlette import status

from api.errors.validation_error import ValidationError
from db.errors import EntityDoesNotExist
from db.repositories.workspaces import WorkspaceTemplateRepository
from models.domain.resource_template import Parameter
from models.schemas.workspace import WorkspaceInCreate
from resources import strings


class ValidateRequest:
    """
    Implements methods to validate API requests.
    """

    @staticmethod
    def validate_workspace_request(workspace_create: WorkspaceInCreate, workspace_template_repo: WorkspaceTemplateRepository):
        validation_errors = []
        try:
            template = workspace_template_repo.get_current_workspace_template_by_name(workspace_create.workspaceType)
        except EntityDoesNotExist:
            validation_errors.append(strings.WORKSPACE_TEMPLATE_X_DOES_NOT_EXIST.format(workspace_create.workspaceType))

        if not validation_errors:
            validation_errors = ValidateRequest.validate_parameters(template.parameters, workspace_create.parameters)

        if validation_errors:
            raise ValidationError(errors=validation_errors, model=template)

    @staticmethod
    def validate_parameters(template_parameters: [Parameter], workspace_create_parameters: dict):
        validation_errors = []
        for parameter in template_parameters:
            name = parameter.name
            create_parameter = workspace_create_parameters.get(name)
            if parameter.required and not create_parameter:
                validation_errors.append(strings.PARAMETER_X_IS_REQUIRED.format(name))

        return validation_errors

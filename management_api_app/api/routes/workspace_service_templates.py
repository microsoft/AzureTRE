from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from api.dependencies.database import get_repository
from db.errors import EntityVersionExist
from db.repositories.resource_templates import ResourceTemplateRepository
from models.domain.resource import ResourceType
from models.schemas.resource_template import ResourceTemplateInResponse, ResourceTemplateInformationInList
from models.schemas.workspace_service_template import WorkspaceServiceTemplateInCreate, WorkspaceServiceTemplateInResponse
from resources import strings
from services.authentication import get_current_admin_user
from services.concatjsonschema import enrich_workspace_service_schema_defs
from services.resource_template_service import create_template_by_resource_type


router = APIRouter(dependencies=[Depends(get_current_admin_user)])


@router.get("/workspace-service-templates", response_model=ResourceTemplateInformationInList, name=strings.API_GET_WORKSPACE_SERVICE_TEMPLATES)
async def get_workspace_service_templates(
        workspace_service_template_repo: ResourceTemplateRepository = Depends(get_repository(ResourceTemplateRepository))
) -> ResourceTemplateInformationInList:
    workspace_service_templates = workspace_service_template_repo.get_basic_resource_templates_information(ResourceType.WorkspaceService)
    return ResourceTemplateInformationInList(templates=workspace_service_templates)


@router.post("/workspace-service-templates", status_code=status.HTTP_201_CREATED,
             response_model=WorkspaceServiceTemplateInResponse, name=strings.API_CREATE_WORKSPACE_SERVICE_TEMPLATES)
async def create_workspace_service_template(
        workspace_template_create: WorkspaceServiceTemplateInCreate,
        workspace_template_repo: ResourceTemplateRepository = Depends(get_repository(ResourceTemplateRepository)),
) -> ResourceTemplateInResponse:
    try:
        template_created = create_template_by_resource_type(workspace_template_create,
                                                            workspace_template_repo,
                                                            ResourceType.WorkspaceService)
        template = enrich_workspace_service_schema_defs(template_created)
        return template
    except EntityVersionExist:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=strings.WORKSPACE_TEMPLATE_VERSION_EXISTS)

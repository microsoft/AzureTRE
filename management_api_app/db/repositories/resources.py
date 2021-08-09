import uuid
from typing import List

from azure.cosmos import CosmosClient
from pydantic import parse_obj_as, UUID4

from core import config
from resources import strings
from db.errors import EntityDoesNotExist
from models.domain.workspace import Workspace
from db.repositories.base import BaseRepository
from models.domain.resource import Deployment, Status, ResourceType
from models.domain.resource_template import ResourceTemplate
from models.schemas.workspace import WorkspaceInCreate
from db.repositories.resource_templates import ResourceTemplateRepository
from services.concatjsonschema import enrich_workspace_schema_defs
from jsonschema import validate
from services.authentication import extract_auth_information


class ResourceRepository(BaseRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client, config.STATE_STORE_RESOURCES_CONTAINER)

    @staticmethod
    def _active_workspaces_query():
        return 'SELECT * FROM c WHERE c.isDeleted = false'

    @staticmethod
    def _validate_workspace_parameters(workspace_create, workspace_template):
        validate(instance=workspace_create["properties"], schema=workspace_template)

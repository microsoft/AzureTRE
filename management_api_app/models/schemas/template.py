from typing import Dict
from pydantic import BaseModel, Field

from models.domain.resource_template import ResourceTemplate, Property


class TemplateInCreate(BaseModel):
    name: str = Field(title="Template name")
    version: str = Field(title="Template version")
    current: bool = Field(title="Mark this version as current")
    json_schema: Dict = Field(title="JSON Schema compliant template")


class TemplateInResponse(ResourceTemplate):
    system_properties: Dict[str, Property] = Field(title="System properties")

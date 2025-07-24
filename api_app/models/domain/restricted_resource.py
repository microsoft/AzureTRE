from typing import Optional, List, Dict, Any
from pydantic import Field, field_validator
from models.domain.resource import AvailableUpgrade, ResourceType
from models.domain.authentication import User
from models.domain.azuretremodel import AzureTREModel


class RestrictedProperties(AzureTREModel):
    display_name: str = ""
    description: str = ""
    overview: str = ""
    connection_uri: str = ""
    is_exposed_externally: bool = True


class RestrictedResource(AzureTREModel):
    """
    Resource request
    """
    id: str = Field(title="Id", description="GUID identifying the resource request")
    templateName: str = Field(title="Resource template name", description="The resource template (bundle) to deploy")
    templateVersion: str = Field(title="Resource template version", description="The version of the resource template (bundle) to deploy")
    properties: Dict[str, Any] = Field(default_factory=dict, title="Restricted Properties", description="Resource properties safe to share with non-admins")
    availableUpgrades: Optional[List[AvailableUpgrade]] = Field(title="Available template upgrades", description="Versions of the template that are available for upgrade")
    isEnabled: bool = True  # Must be set before a resource can be deleted
    resourceType: ResourceType
    deploymentStatus: Optional[str] = Field(title="Deployment Status", description="Overall deployment status of the resource")
    etag: str = Field(title="_etag", description="eTag of the document", alias="_etag")
    resourcePath: str = ""
    resourceVersion: int = 0
    user: Optional[User] = Field(default=None)
    updatedWhen: float = 0

    @field_validator('properties', mode='before')
    @classmethod
    def convert_properties_to_restricted(cls, v):
        """Convert properties dict to filtered dict containing only safe fields."""
        if v is None:
            v = {}
        if isinstance(v, dict):
            # Extract only the fields that RestrictedProperties supports
            return {
                "display_name": v.get("display_name", ""),
                "description": v.get("description", ""),
                "overview": v.get("overview", ""),
                "connection_uri": v.get("connection_uri", ""),
                "is_exposed_externally": v.get("is_exposed_externally", True)
            }
        elif hasattr(v, 'model_dump'):
            # If it's a Pydantic model, convert to dict first
            v_dict = v.model_dump()
            return {
                "display_name": v_dict.get("display_name", ""),
                "description": v_dict.get("description", ""),
                "overview": v_dict.get("overview", ""),
                "connection_uri": v_dict.get("connection_uri", ""),
                "is_exposed_externally": v_dict.get("is_exposed_externally", True)
            }
        return v

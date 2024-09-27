from typing import Optional, List
from pydantic import Field
from models.domain.resource import AvailableUpgrade, ResourceType
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
    properties: RestrictedProperties = Field(None, title="Restricted Properties", description="Resource properties safe to share with non-admins")
    availableUpgrades: Optional[List[AvailableUpgrade]] = Field(title="Available template upgrades", description="Versions of the template that are available for upgrade")
    isEnabled: bool = True  # Must be set before a resource can be deleted
    resourceType: ResourceType
    deploymentStatus: Optional[str] = Field(title="Deployment Status", description="Overall deployment status of the resource")
    etag: str = Field(title="_etag", description="eTag of the document", alias="_etag")
    resourcePath: str = ""
    resourceVersion: int = 0
    user: dict = {}
    updatedWhen: float = 0

from pydantic import BaseModel


class Metadata(BaseModel):
    api_version: str
    api_client_id: str
    api_root_scope: str
    aad_tenant_id: str

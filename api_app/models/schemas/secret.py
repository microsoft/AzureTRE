from pydantic import BaseModel, Field


class SecretInResponse(BaseModel):
    key: str = Field("", title="Property name", description="Name of the resource property that references the secret")
    value: str = Field("", title="Secret value", description="The secret value retrieved from the workspace Key Vault")

    class Config:
        schema_extra = {
            "example": {
                "key": "admin_password_keyvault_secret_id",
                "value": "a-very-secret-value"
            }
        }

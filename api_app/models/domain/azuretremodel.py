from pydantic import BaseModel, ConfigDict


class AzureTREModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

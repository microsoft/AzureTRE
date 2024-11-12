from pydantic import ConfigDict, BaseModel


class AzureTREModel(BaseModel):
    class Config(ConfigDict):
        populate_by_name = True
        arbitrary_types_allowed = True

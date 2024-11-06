from pydantic import ConfigDict, BaseModel


class AzureTREModel(BaseModel):
    class Config(ConfigDict):
        allow_population_by_field_name = True
        arbitrary_types_allowed = True

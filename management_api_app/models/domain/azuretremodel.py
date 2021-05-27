from pydantic import BaseConfig, BaseModel


class AzureTREModel(BaseModel):
    class Config(BaseConfig):
        allow_population_by_field_name = True
        arbitrary_types_allowed = True

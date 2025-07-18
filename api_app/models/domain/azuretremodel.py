try:
    # Pydantic v2
    from pydantic import BaseModel, ConfigDict
    
    class AzureTREModel(BaseModel):
        model_config = ConfigDict(
            populate_by_name=True,
            arbitrary_types_allowed=True
        )
except ImportError:
    # Pydantic v1 fallback
    from pydantic import BaseConfig, BaseModel
    
    class AzureTREModel(BaseModel):
        class Config(BaseConfig):
            allow_population_by_field_name = True
            arbitrary_types_allowed = True

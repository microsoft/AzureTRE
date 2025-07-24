from pydantic import BaseModel, ConfigDict, model_serializer
import warnings


class AzureTREModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

    @model_serializer(mode='wrap')
    def serialize_model(self, serializer, info):
        """
        Custom serializer for database operations.

        Why this is needed:
        1. Our models use Optional[User] typing for type safety in application code
        2. Database loading sometimes results in dict values in User fields (not User objects)
        3. This creates mixed state: field typed as User but containing dict
        4. Pydantic warns about this type mismatch during model_dump()
        5. But the functionality works fine - dicts serialize correctly to database
        6. So we suppress the warnings since they're just noise for database operations
        """
        # Suppress User serialization warnings during model_dump for database operations
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            data = serializer(self)

        return data

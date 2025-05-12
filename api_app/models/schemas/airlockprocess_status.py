from pydantic import BaseModel

class AirlockProcessStatus(BaseModel):
    status:int
    message:str

    class config:
        schema_extra= {
            "example" :  {
                "status": 1,
                "message": "message updated"
            }
        }


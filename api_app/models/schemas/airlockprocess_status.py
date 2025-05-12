from pydantic import BaseModel

def getAirlockStatus(status:int):
    return {
        "status":status
    }

def getAirlockMessage(message:str):
    return {
        "message": message
    }
class AirlockStatus(BaseModel):
    status:int=getAirlockStatus("status")
    message:str=getAirlockMessage("message")

    class config:
        schema_extra= {
            "example" :  {
                "status": getAirlockStatus("status"),
                "message": getAirlockMessage("message")
            }
        }


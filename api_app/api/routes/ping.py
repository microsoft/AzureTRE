from fastapi import APIRouter
from resources import strings

router = APIRouter()


@router.get("/ping", name=strings.API_GET_PING)
@router.get("/", name=strings.API_GET_PING)
def ping() -> str:
    # The ping endpoint is a simple endpoint that can be called by the Application Gateway
    # to test if it is able to reach the API
    return "pong"

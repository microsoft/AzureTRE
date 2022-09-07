from fastapi import APIRouter, Depends

from db.repositories.operations import OperationRepository
from api.dependencies.database import get_repository
from models.schemas.operation import OperationInList
from resources import strings
from services.authentication import get_current_tre_user_or_tre_admin


operations_router = APIRouter(dependencies=[Depends(get_current_tre_user_or_tre_admin)])


@operations_router.get("/operations", response_model=OperationInList, name=strings.API_GET_MY_OPERATIONS)
async def get_my_operations(user=Depends(get_current_tre_user_or_tre_admin), operations_repo=Depends(get_repository(OperationRepository))) -> OperationInList:
    operations = operations_repo.get_my_operations(user_id=user.id)
    return OperationInList(operations=operations)

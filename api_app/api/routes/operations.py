from fastapi import APIRouter, Depends

from api.helpers import get_repository
from db.repositories.operations import OperationRepository
from models.schemas.operation import OperationInList
from resources import strings
from auth.rbac import require_tre_user_or_admin


operations_router = APIRouter(dependencies=[Depends(require_tre_user_or_admin)])


@operations_router.get("/operations", response_model=OperationInList, name=strings.API_GET_MY_OPERATIONS)
async def get_my_operations(user=Depends(require_tre_user_or_admin), operations_repo=Depends(get_repository(OperationRepository))) -> OperationInList:
    operations = await operations_repo.get_my_operations(user_id=user.id)
    return OperationInList(operations=operations)

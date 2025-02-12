from fastapi import APIRouter, Depends, HTTPException, status as status_code
from typing import List, Optional

from api.helpers import get_repository
from resources import strings
from db.repositories.airlock_requests import AirlockRequestRepository
from models.domain.airlock_request import AirlockRequest, AirlockRequestStatus, AirlockRequestType
from services.authentication import get_current_tre_user_or_tre_admin

router = APIRouter(dependencies=[Depends(get_current_tre_user_or_tre_admin)])


@router.get("/requests", response_model=List[AirlockRequest], name=strings.API_LIST_REQUESTS)
async def get_requests(
    user=Depends(get_current_tre_user_or_tre_admin),
    airlock_request_repo: AirlockRequestRepository = Depends(get_repository(AirlockRequestRepository)),
    airlock_manager: bool = False,
    creator_user_id: Optional[str] = None, type: Optional[AirlockRequestType] = None, status: Optional[AirlockRequestStatus] = None,
        order_by: Optional[str] = None, order_ascending: bool = True
) -> List[AirlockRequest]:
    try:
        if not airlock_manager:
            requests = await airlock_request_repo.get_airlock_requests(
                creator_user_id=creator_user_id or user.id,
                type=type,
                status=status,
                order_by=order_by,
                order_ascending=order_ascending,
            )
        else:
            requests = await airlock_request_repo.get_airlock_requests_for_airlock_manager(user)

        return requests

    except ValueError as ve:
        raise HTTPException(status_code=status_code.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status_code.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

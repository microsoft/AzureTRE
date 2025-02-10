from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import UUID4

from api.dependencies.database import get_repository
from db.repositories.airlock_requests import AirlockRequestRepository
from models.domain.airlock_request import AirlockRequest
from services.authentication import get_current_tre_user_or_tre_admin

router = APIRouter()

@router.get("/requests", response_model=List[AirlockRequest], name="get_requests")
async def get_requests(
    workspace_id: Optional[UUID4] = None,
    user=Depends(get_current_tre_user_or_tre_admin),
    airlock_request_repo=Depends(get_repository(AirlockRequestRepository))
) -> List[AirlockRequest]:
    try:
        requests = await airlock_request_repo.get_airlock_requests(workspace_id=workspace_id, creator_user_id=user.id, order_by="createdWhen", order_ascending=False)
        return requests
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

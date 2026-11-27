from typing import Callable

from fastapi import Depends, HTTPException, Path, status
from pydantic import UUID4

from api.helpers import get_repository
from db.errors import EntityDoesNotExist
from db.repositories.operations import OperationRepository
from models.domain.operation import Operation
from models.domain.resource import Resource
from resources import strings


def get_operation_by_id_from_path(resource_dependency: Callable) -> Callable:
    async def _get_operation(
        operation_id: UUID4 = Path(...),
        resource: Resource = Depends(resource_dependency),
        operations_repo=Depends(get_repository(OperationRepository)),
    ) -> Operation:
        try:
            return await operations_repo.get_operation_by_id_for_resource(
                operation_id=str(operation_id), resource_id=resource.id
            )
        except EntityDoesNotExist:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.OPERATION_DOES_NOT_EXIST)

    return _get_operation

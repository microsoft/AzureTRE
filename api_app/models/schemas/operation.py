from typing import List
from pydantic import BaseModel, Field
from models.domain.operation import Operation


def get_sample_operation(operation_id: str) -> dict:
    return {
        "id": operation_id,
        "resourceId": "933ad738-7265-4b5f-9eae-a1a62928772e",
        "resourcePath": "/workspaces/933ad738-7265-4b5f-9eae-a1a62928772e",
        "resourceVersion": 0,
        "status": "awaiting_deployment",
        "action": "install",
        "message": "",
        "createdWhen": 1642611942.423857,
        "updatedWhen": 1642611942.423857,
        "steps": [
            {
                "stepId": "main",
                "stepTitle": "deployment for main",
                "resourceId": "933ad738-7265-4b5f-9eae-a1a62928772e",
                "resourceTemplateName": "tre-workspace-base",
                "resourceType": "workspace",
                "resourceAction": "install",
                "status": "awaiting_deployment",
                "updatedWhen": 1642611942.423857
            }
        ]
    }


class OperationInResponse(BaseModel):
    operation: Operation

    class Config:
        schema_extra = {
            "example": {
                "operation": get_sample_operation("7ac667f0-fd3f-4a6c-815b-82d0cb7a2132")
            }
        }


class OperationInList(BaseModel):
    operations: List[Operation] = Field([], title="Operations")

    class Config:
        schema_extra = {
            "example": {
                "operations": [
                    get_sample_operation("7ac667f0-fd3f-4a6c-815b-82d0cb7a2132"),
                    get_sample_operation("640488fe-9408-4b9f-a239-3b03bc0c5df0")
                ]
            }
        }

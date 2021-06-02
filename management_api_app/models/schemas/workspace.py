from typing import List
from pydantic import BaseModel

from models.domain.workspace import Workspace


class WorkspaceInResponse(BaseModel):
    workspace: Workspace

    class Config:
        schema_extra = {
            "example": {
                "workspace": {
                    "id": "933ad738-7265-4b5f-9eae-a1a62928772e",
                    "resourceSpec": {
                        "name": "My workspace",
                        "version": "0.1.0",
                        "parameters": [
                            {
                                "name": "location",
                                "value": "westeurope"
                            },
                            {
                                "name": "workspace_id",
                                "value": "0001"
                            },
                            {
                                "name": "core_id",
                                "value": "mytre-dev-1234"
                            },
                            {
                                "name": "address_space",
                                "value": "10.2.1.0/24"
                            }
                        ]
                    },
                    "resourceType": "workspace",
                    "status": "not_deployed",
                    "isDeleted": False,
                    "friendlyName": "hello",
                    "description": "some description",
                    "workspaceURL": ""
                }
            }
        }


class WorkspacesInList(BaseModel):
    workspaces: List[Workspace]

    class Config:
        schema_extra = {
            "example": {
                "workspaces": [
                    {
                        "id": "933ad738-7265-4b5f-9eae-a1a62928772e",
                        "resourceSpec": {
                            "name": "My workspace",
                            "version": "0.1.0",
                            "parameters": [
                                {
                                    "name": "location",
                                    "value": "westeurope"
                                },
                                {
                                    "name": "workspace_id",
                                    "value": "0001"
                                },
                                {
                                    "name": "core_id",
                                    "value": "mytre-dev-1234"
                                },
                                {
                                    "name": "address_space",
                                    "value": "10.2.1.0/24"
                                }
                            ]
                        },
                        "resourceType": "workspace",
                        "status": "not_deployed",
                        "isDeleted": False,
                        "friendlyName": "my friendly name",
                        "description": "some description",
                        "workspaceURL": ""
                    },
                    {
                        "id": "2fdc9fba-726e-4db6-a1b8-9018a2165748",
                        "resourceSpec": {
                            "name": "My workspace",
                            "version": "0.1.0",
                            "parameters": [
                                {
                                    "name": "location",
                                    "value": "westeurope"
                                },
                                {
                                    "name": "workspace_id",
                                    "value": "0002"
                                },
                                {
                                    "name": "core_id",
                                    "value": "mytre-dev-3142"
                                },
                                {
                                    "name": "address_space",
                                    "value": "10.2.1.0/24"
                                }
                            ]
                        },
                        "resourceType": "workspace",
                        "status": "not_deployed",
                        "isDeleted": False,
                        "friendlyName": "my friendly name",
                        "description": "some description",
                        "workspaceURL": ""
                    }
                ]
            }
        }


class WorkspaceInCreate(BaseModel):
    friendlyName: str
    workspaceType: str
    description: str

    class Config:
        schema_extra = {
            "example": {
                "friendlyName": "My workspace",
                "description": "workspace for team X",
                "workspaceType": "tre-workspace-vanilla",
            }
        }


class WorkspaceIdInResponse(BaseModel):
    workspaceId: str

    class Config:
        schema_extra = {
            "example": {
                "workspaceId": "49a7445c-aae6-41ec-a539-30dfa90ab1ae",
            }
        }

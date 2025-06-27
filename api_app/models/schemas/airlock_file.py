from typing import List
from pydantic import BaseModel, Field


class AirlockFileMetadata(BaseModel):
    name: str = Field(..., title="File name", description="Name of the file")
    size: int = Field(..., title="File size", description="Size of the file in bytes")
    lastModified: int = Field(..., title="Last modified", description="Last modified timestamp")


class AirlockFileListResponse(BaseModel):
    files: List[AirlockFileMetadata] = Field([], title="Files", description="List of files in the airlock request")

    class Config:
        schema_extra = {
            "example": {
                "files": [
                    {
                        "name": "data.csv",
                        "size": 1024,
                        "lastModified": 1672531200
                    },
                    {
                        "name": "analysis.zip",
                        "size": 2048,
                        "lastModified": 1672531300
                    }
                ]
            }
        }


class AirlockFileUploadResponse(BaseModel):
    message: str = Field(..., title="Message", description="Success message")
    fileName: str = Field(..., title="File name", description="Name of the uploaded file")
    size: int = Field(..., title="File size", description="Size of the uploaded file")

    class Config:
        schema_extra = {
            "example": {
                "message": "File uploaded successfully",
                "fileName": "data.csv",
                "size": 1024
            }
        }
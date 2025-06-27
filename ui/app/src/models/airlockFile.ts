export interface AirlockFileMetadata {
  name: string;
  size: number;
  lastModified: number;
}

export interface AirlockFileListResponse {
  files: AirlockFileMetadata[];
}

export interface AirlockFileUploadResponse {
  message: string;
  fileName: string;
  size: number;
}
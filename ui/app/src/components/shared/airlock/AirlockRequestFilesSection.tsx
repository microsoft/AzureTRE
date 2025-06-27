import {
  MessageBar,
  MessageBarType,
  Pivot,
  PivotItem,
  PrimaryButton,
  Stack,
  TextField,
  TooltipHost,
  DefaultButton,
  IconButton,
  Spinner,
  SpinnerSize,
  DocumentCard,
  DocumentCardTitle,
  DocumentCardPreview,
  DocumentCardStatus,
  DocumentCardActions,
  List,
} from "@fluentui/react";
import React, { useCallback, useEffect, useState, useRef } from "react";
import { HttpMethod, useAuthApiCall } from "../../../hooks/useAuthApiCall";
import { AirlockRequest, AirlockRequestStatus } from "../../../models/airlock";
import { ApiEndpoint } from "../../../models/apiEndpoints";
import { APIError } from "../../../models/exceptions";
import { ExceptionLayout } from "../ExceptionLayout";
import { CliCommand } from "../CliCommand";
import { AirlockFileMetadata, AirlockFileListResponse, AirlockFileUploadResponse } from "../../../models/airlockFile";
import config from "../../../config.json";

interface AirlockRequestFilesSectionProps {
  request: AirlockRequest;
  workspaceApplicationIdURI: string;
}

export const AirlockRequestFilesSection: React.FunctionComponent<
  AirlockRequestFilesSectionProps
> = (props: AirlockRequestFilesSectionProps) => {
  const COPY_TOOL_TIP_DEFAULT_MESSAGE = "Copy to clipboard";

  const [copyToolTipMessage, setCopyToolTipMessage] = useState<string>(
    COPY_TOOL_TIP_DEFAULT_MESSAGE,
  );
  const [sasUrl, setSasUrl] = useState<string>();

  const [sasUrlError, setSasUrlError] = useState(false);
  const [apiSasUrlError, setApiSasUrlError] = useState({} as APIError);

  // Direct upload/download state
  const [files, setFiles] = useState<AirlockFileMetadata[]>([]);
  const [filesLoading, setFilesLoading] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [fileListError, setFileListError] = useState<APIError | null>(null);
  const [uploadError, setUploadError] = useState<APIError | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const apiCall = useAuthApiCall();

  const generateSasUrl = useCallback(async () => {
    if (props.request && props.request.workspaceId) {
      try {
        const linkObject = await apiCall(
          `${ApiEndpoint.Workspaces}/${props.request.workspaceId}/${ApiEndpoint.AirlockRequests}/${props.request.id}/${ApiEndpoint.AirlockLink}`,
          HttpMethod.Get,
          props.workspaceApplicationIdURI,
        );
        setSasUrl(linkObject.containerUrl);
      } catch (err: any) {
        err.userMessage = "Error retrieving storage link";
        setApiSasUrlError(err);
        setSasUrlError(true);
      }
    }
  }, [apiCall, props.request, props.workspaceApplicationIdURI]);

  const parseSasUrl = (sasUrl: string) => {
    const match = sasUrl.match(
      /https:\/\/(.*?).blob.core.windows.net\/(.*)\?(.*)$/,
    );
    if (!match) {
      return;
    }

    return {
      StorageAccountName: match[1],
      containerName: match[2],
      sasToken: match[3],
    };
  };

  const handleCopySasUrl = () => {
    if (!sasUrl) {
      return;
    }
    navigator.clipboard.writeText(sasUrl);
    setCopyToolTipMessage("Copied");
    setTimeout(
      () => setCopyToolTipMessage(COPY_TOOL_TIP_DEFAULT_MESSAGE),
      3000,
    );
  };

  const getAzureCliCommand = (sasUrl: string) => {
    let containerDetails = parseSasUrl(sasUrl);
    if (!containerDetails) {
      return "";
    }

    let cliCommand = "";
    if (props.request.status === AirlockRequestStatus.Draft) {
      cliCommand = `az storage blob upload --file </path/to/file> --name <filename.filetype> --account-name ${containerDetails.StorageAccountName} --type block --container-name ${containerDetails.containerName} --sas-token "${containerDetails.sasToken}"`;
    } else {
      cliCommand = `az storage blob download-batch --destination </destination/path/for/file> --source ${containerDetails.containerName} --account-name ${containerDetails.StorageAccountName} --sas-token "${containerDetails.sasToken}"`;
    }

    return cliCommand;
  };

  // File operations functions
  const loadFiles = useCallback(async () => {
    if (props.request && props.request.workspaceId) {
      setFilesLoading(true);
      setFileListError(null);
      try {
        const response: AirlockFileListResponse = await apiCall(
          `${ApiEndpoint.Workspaces}/${props.request.workspaceId}/${ApiEndpoint.AirlockRequests}/${props.request.id}/${ApiEndpoint.AirlockFiles}`,
          HttpMethod.Get,
          props.workspaceApplicationIdURI,
        );
        setFiles(response.files || []);
      } catch (err: any) {
        err.userMessage = "Error loading files";
        setFileListError(err);
      } finally {
        setFilesLoading(false);
      }
    }
  }, [apiCall, props.request, props.workspaceApplicationIdURI]);

  const handleFileUpload = async (file: File) => {
    setUploadLoading(true);
    setUploadError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);

      // We need to make a direct fetch call for file upload as the useAuthApiCall doesn't handle FormData properly
      const tokenRequest = {
        scopes: [`${props.workspaceApplicationIdURI || config.treApplicationId}/user_impersonation`],
      };
      
      // This is a simplified approach - in production you'd want to use the proper auth mechanism
      const response = await fetch(
        `${config.treUrl}/${ApiEndpoint.Workspaces}/${props.request.workspaceId}/${ApiEndpoint.AirlockRequests}/${props.request.id}/${ApiEndpoint.AirlockFiles}`,
        {
          method: 'POST',
          body: formData,
          // Note: Don't set Content-Type header when sending FormData - browser will set it automatically with boundary
        }
      );
      
      if (!response.ok) {
        throw new Error('Upload failed');
      }
      
      const result: AirlockFileUploadResponse = await response.json();
      
      // Reload the file list after successful upload
      await loadFiles();
    } catch (err: any) {
      err.userMessage = "Error uploading file";
      setUploadError(err);
    } finally {
      setUploadLoading(false);
    }
  };

  const handleFileInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      handleFileUpload(file);
    }
    // Reset the input so the same file can be uploaded again if needed
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDownloadFile = async (fileName: string) => {
    try {
      // Use a blob URL approach with the API call
      window.location.href = `${config.treUrl}/${ApiEndpoint.Workspaces}/${props.request.workspaceId}/${ApiEndpoint.AirlockRequests}/${props.request.id}/${ApiEndpoint.AirlockFiles}/${encodeURIComponent(fileName)}`;
    } catch (err: any) {
      console.error('Download failed:', err);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  useEffect(() => {
    generateSasUrl();
    loadFiles();
  }, [generateSasUrl, loadFiles]);

  return (
    <Stack>
      <Pivot aria-label="Storage options">
        <PivotItem headerText="SAS URL">
          <Stack>
            <Stack.Item style={{ paddingTop: "10px", paddingBottom: "10px" }}>
              {props.request.status === AirlockRequestStatus.Draft ? (
                <small>
                  Use the storage container SAS URL to upload your request file.
                </small>
              ) : (
                <small>
                  Use the storage container SAS URL to view the request file.
                </small>
              )}
              <Stack
                horizontal
                styles={{ root: { alignItems: "center", paddingTop: "7px" } }}
              >
                <Stack.Item grow>
                  <TextField readOnly value={sasUrl} />
                </Stack.Item>
                <TooltipHost content={copyToolTipMessage}>
                  <PrimaryButton
                    iconProps={{ iconName: "copy" }}
                    styles={{ root: { minWidth: "40px" } }}
                    onClick={() => {
                      handleCopySasUrl();
                    }}
                  />
                </TooltipHost>
              </Stack>
            </Stack.Item>
            {props.request.status === AirlockRequestStatus.Draft && (
              <MessageBar messageBarType={MessageBarType.info}>
                Please upload a single file. Only single-file imports (including
                zip files) are supported.
              </MessageBar>
            )}
          </Stack>
        </PivotItem>
        <PivotItem headerText="CLI">
          <Stack>
            <Stack.Item style={{ paddingTop: "10px", paddingBottom: "10px" }}>
              <small>
                Use Azure command-line interface (Azure CLI) to interact with
                the storage container.
              </small>
              <hr
                style={{ border: "1px solid #faf9f8", borderRadius: "1px" }}
              />
            </Stack.Item>
            <Stack.Item style={{ paddingTop: "10px" }}>
              <CliCommand
                command={sasUrl ? getAzureCliCommand(sasUrl) : ""}
                title={
                  props.request.status === AirlockRequestStatus.Draft
                    ? "Upload a file to the storage container"
                    : "Download the file from the storage container"
                }
                isLoading={!sasUrl && !sasUrlError}
              />
            </Stack.Item>
          </Stack>
        </PivotItem>
        <PivotItem headerText="Direct Upload">
          <Stack>
            <Stack.Item style={{ paddingTop: "10px", paddingBottom: "10px" }}>
              {props.request.status === AirlockRequestStatus.Draft ? (
                <small>
                  Upload files directly through the browser without using SAS tokens.
                </small>
              ) : (
                <small>
                  View and download files directly through the browser.
                </small>
              )}
              <hr
                style={{ border: "1px solid #faf9f8", borderRadius: "1px" }}
              />
            </Stack.Item>
            
            {/* Upload section for Draft requests */}
            {props.request.status === AirlockRequestStatus.Draft && (
              <Stack.Item style={{ paddingTop: "10px" }}>
                <Stack horizontal tokens={{ childrenGap: 10 }}>
                  <DefaultButton
                    iconProps={{ iconName: "Upload" }}
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploadLoading}
                  >
                    {uploadLoading ? "Uploading..." : "Upload File"}
                  </DefaultButton>
                  {uploadLoading && <Spinner size={SpinnerSize.small} />}
                </Stack>
                <input
                  type="file"
                  ref={fileInputRef}
                  style={{ display: "none" }}
                  onChange={handleFileInputChange}
                />
                {uploadError && <ExceptionLayout e={uploadError} />}
                <MessageBar messageBarType={MessageBarType.info}>
                  Please upload a single file. Only single-file imports (including
                  zip files) are supported.
                </MessageBar>
              </Stack.Item>
            )}

            {/* File list section */}
            <Stack.Item style={{ paddingTop: "10px" }}>
              <Stack horizontal tokens={{ childrenGap: 10 }} verticalAlign="center">
                <h4>Files in this request:</h4>
                <IconButton
                  iconProps={{ iconName: "Refresh" }}
                  title="Refresh file list"
                  onClick={loadFiles}
                  disabled={filesLoading}
                />
                {filesLoading && <Spinner size={SpinnerSize.small} />}
              </Stack>
              
              {fileListError && <ExceptionLayout e={fileListError} />}
              
              {files.length === 0 && !filesLoading && !fileListError && (
                <MessageBar messageBarType={MessageBarType.info}>
                  No files found in this request.
                </MessageBar>
              )}
              
              {files.length > 0 && (
                <Stack styles={{ root: { maxHeight: "400px", overflowY: "auto" } }}>
                  {files.map((file, index) => (
                    <DocumentCard
                      key={index}
                      styles={{ root: { margin: "5px 0", maxWidth: "100%" } }}
                    >
                      <DocumentCardPreview 
                        previewImages={[{
                          name: file.name,
                          url: "",
                          iconSrc: "",
                          width: 40,
                          height: 40
                        }]}
                      />
                      <Stack horizontal styles={{ root: { padding: "10px", flex: 1 } }}>
                        <Stack.Item grow>
                          <DocumentCardTitle title={file.name} shouldTruncate />
                          <Stack horizontal tokens={{ childrenGap: 15 }}>
                            <small>Size: {formatFileSize(file.size)}</small>
                            <small>Modified: {formatDate(file.lastModified)}</small>
                          </Stack>
                        </Stack.Item>
                        <DocumentCardActions
                          actions={[
                            {
                              iconProps: { iconName: "Download" },
                              ariaLabel: "Download file",
                              onClick: () => handleDownloadFile(file.name),
                            },
                          ]}
                        />
                      </Stack>
                    </DocumentCard>
                  ))}
                </Stack>
              )}
            </Stack.Item>
          </Stack>
        </PivotItem>
      </Pivot>
      {sasUrlError && <ExceptionLayout e={apiSasUrlError} />}
    </Stack>
  );
};

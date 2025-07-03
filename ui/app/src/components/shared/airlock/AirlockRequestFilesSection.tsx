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
import { AirlockRequest, AirlockRequestStatus, AirlockRequestType } from "../../../models/airlock";
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
  const [uploadSasUrl, setUploadSasUrl] = useState<string>();

  const [sasUrlError, setSasUrlError] = useState(false);
  const [apiSasUrlError, setApiSasUrlError] = useState({} as APIError);
  const [uploadSasUrlError, setUploadSasUrlError] = useState(false);
  const [apiUploadSasUrlError, setApiUploadSasUrlError] = useState({} as APIError);

  // SAS upload state
  const [sasUploadLoading, setSasUploadLoading] = useState(false);
  const [sasUploadError, setSasUploadError] = useState<APIError | null>(null);
  const sasFileInputRef = useRef<HTMLInputElement>(null);

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

  const generateUploadSasUrl = useCallback(async () => {
    // Only generate upload SAS URLs for import requests in Draft status when SAS upload is enabled
    if (props.request &&
      props.request.workspaceId &&
      props.request.status === AirlockRequestStatus.Draft &&
      props.request.type === AirlockRequestType.Import &&
      config.airlockImportSasEnabled) {
      try {
        const linkObject = await apiCall(
          `${ApiEndpoint.Workspaces}/${props.request.workspaceId}/${ApiEndpoint.AirlockRequests}/${props.request.id}/${ApiEndpoint.AirlockUploadLink}`,
          HttpMethod.Get,
          props.workspaceApplicationIdURI,
        );
        setUploadSasUrl(linkObject.containerUrl);
        setUploadSasUrlError(false);
      } catch (err: any) {
        err.userMessage = "Error retrieving upload storage link";
        setApiUploadSasUrlError(err);
        setUploadSasUrlError(true);
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
    // Only load files for import requests since API doesn't have access to export storage accounts
    if (props.request && props.request.workspaceId && props.request.type === AirlockRequestType.Import) {
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

      // Use the proper auth mechanism with the enhanced useAuthApiCall that handles FormData
      const result: AirlockFileUploadResponse = await apiCall(
        `${ApiEndpoint.Workspaces}/${props.request.workspaceId}/${ApiEndpoint.AirlockRequests}/${props.request.id}/${ApiEndpoint.AirlockFiles}`,
        HttpMethod.Post,
        props.workspaceApplicationIdURI,
        formData
      );

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

  const handleSasFileUpload = async (file: File) => {
    if (!uploadSasUrl) {
      const error = new APIError();
      error.userMessage = "Upload SAS URL not available";
      error.message = "No upload URL generated";
      setSasUploadError(error);
      return;
    }

    setSasUploadLoading(true);
    setSasUploadError(null);
    try {
      // Parse the SAS URL to get the proper blob URL
      const sasUrlObject = new URL(uploadSasUrl);
      const baseUrl = `${sasUrlObject.origin}${sasUrlObject.pathname}`;
      const sasToken = sasUrlObject.search;

      // Construct the blob URL with the file name
      const blobUrl = `${baseUrl}/${encodeURIComponent(file.name)}${sasToken}`;

      console.log('Uploading to blob URL:', blobUrl);

      // Upload directly to Azure Storage using the SAS URL
      const response = await fetch(blobUrl, {
        method: 'PUT',
        headers: {
          'x-ms-blob-type': 'BlockBlob',
          'x-ms-version': '2020-04-08',
          'Content-Type': file.type || 'application/octet-stream',
        },
        body: file,
        mode: 'cors',
      });

      if (!response.ok) {
        // Try to get more detailed error information
        let errorText = `${response.status} ${response.statusText}`;
        try {
          const responseText = await response.text();
          if (responseText) {
            errorText += `: ${responseText}`;
          }
        } catch {
          // Ignore if we can't read response text
        }
        throw new Error(`Upload failed: ${errorText}`);
      }

      console.log('Upload successful');
      // Reload the file list after successful upload
      await loadFiles();
    } catch (err: any) {
      console.error('SAS upload error:', err);
      const error = new APIError();
      error.userMessage = "Error uploading file via SAS URL";

      if (err.name === 'TypeError' && err.message.includes('Failed to fetch')) {
        const availableMethods = [];
        if (config.airlockImportDirectUploadEnabled) {
          availableMethods.push('Direct Upload');
        }
        const methodsText = availableMethods.length > 0
          ? `Please use the '${availableMethods.join("' or '")}' method${availableMethods.length > 1 ? 's' : ''} instead`
          : 'Please contact your administrator for alternative upload methods';

        error.message = `Network error: Unable to upload directly to Azure Storage. This is likely due to CORS (Cross-Origin Resource Sharing) policy restrictions on the storage account. ${methodsText}, which uploads through the TRE API and doesn't require CORS configuration.`;
      } else {
        error.message = err.message || err.toString();
      }

      setSasUploadError(error);
    } finally {
      setSasUploadLoading(false);
    }
  };

  const handleSasFileInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      handleSasFileUpload(file);
    }
    // Reset the input so the same file can be uploaded again if needed
    if (sasFileInputRef.current) {
      sasFileInputRef.current.value = '';
    }
  };

  useEffect(() => {
    generateSasUrl();
    generateUploadSasUrl();
    loadFiles();
  }, [generateSasUrl, generateUploadSasUrl, loadFiles]);

  return (
    <Stack>
      <Pivot aria-label="Storage options">
        <PivotItem headerText="SAS URL">
          <Stack>
            <Stack.Item style={{ paddingTop: "10px", paddingBottom: "10px" }}>
              {props.request.status === AirlockRequestStatus.Draft ? (
                <small>
                  Use the storage container SAS URL to view the container (read-only access).
                </small>
              ) : (
                <small>
                  Use the storage container SAS URL to view and download the request files.
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
          </Stack>
        </PivotItem>

        {props.request.status === AirlockRequestStatus.Draft &&
          props.request.type === AirlockRequestType.Import &&
          config.airlockImportSasEnabled && (
            <PivotItem headerText="SAS Upload">
              <Stack>
                <Stack.Item style={{ paddingTop: "10px", paddingBottom: "10px" }}>
                  <small>
                    Upload files directly to Azure Storage using a SAS token with upload permissions.
                  </small>
                  <hr
                    style={{ border: "1px solid #faf9f8", borderRadius: "1px" }}
                  />
                </Stack.Item>

                <Stack.Item style={{ paddingTop: "10px" }}>
                  <Stack horizontal tokens={{ childrenGap: 10 }}>
                    <DefaultButton
                      iconProps={{ iconName: "Upload" }}
                      onClick={() => sasFileInputRef.current?.click()}
                      disabled={sasUploadLoading || !uploadSasUrl}
                    >
                      {sasUploadLoading ? "Uploading..." : "Upload File via SAS"}
                    </DefaultButton>
                    {sasUploadLoading && <Spinner size={SpinnerSize.small} />}
                  </Stack>
                  <input
                    type="file"
                    ref={sasFileInputRef}
                    style={{ display: "none" }}
                    onChange={handleSasFileInputChange}
                  />
                  {sasUploadError && <ExceptionLayout e={sasUploadError} />}
                  {uploadSasUrlError && <ExceptionLayout e={apiUploadSasUrlError} />}
                  <MessageBar messageBarType={MessageBarType.info}>
                    This method uploads files directly to Azure Storage using SAS tokens.
                    If you encounter "Failed to fetch" errors, this may be due to CORS policy restrictions.
                    {config.airlockImportDirectUploadEnabled &&
                      " In that case, please use the \"Direct Upload\" method instead."
                    }
                    Please upload a single file. Only single-file imports (including zip files) are supported.
                  </MessageBar>
                </Stack.Item>
              </Stack>
            </PivotItem>
          )}

        {(props.request.type === AirlockRequestType.Export ||
          (props.request.type === AirlockRequestType.Import && config.airlockImportSasEnabled)) && (
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
          )}

        {props.request.type === AirlockRequestType.Import && config.airlockImportDirectUploadEnabled && (
          <PivotItem headerText="Direct Upload">
            <Stack>
              <Stack.Item style={{ paddingTop: "10px", paddingBottom: "10px" }}>
                {props.request.status === AirlockRequestStatus.Draft ? (
                  <small>
                    Upload files directly through the browser using authenticated API calls.
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
                      {uploadLoading ? "Uploading..." : "Upload File (Direct)"}
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
                    This method uses authenticated API calls for upload.
                    Please upload a single file. Only single-file imports (including zip files) are supported.
                  </MessageBar>
                </Stack.Item>
              )}              {/* File list section - only visible on Direct Upload tab for import requests */}
              {props.request.type === AirlockRequestType.Import && (
                <Stack style={{ paddingTop: "20px" }}>
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
                </Stack>
              )}
            </Stack>
          </PivotItem>
        )}
      </Pivot>

      {sasUrlError && <ExceptionLayout e={apiSasUrlError} />}
    </Stack>
  );
};

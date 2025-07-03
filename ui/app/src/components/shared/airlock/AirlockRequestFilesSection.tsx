import {
  MessageBar,
  MessageBarType,
  Pivot,
  PivotItem,
  PrimaryButton,
  Stack,
  TextField,
  TooltipHost,
  ProgressIndicator
} from "@fluentui/react";
import React, { useCallback, useEffect, useState } from "react";
import { HttpMethod, useAuthApiCall } from "../../../hooks/useAuthApiCall";
import { AirlockRequest, AirlockRequestStatus } from "../../../models/airlock";
import { ApiEndpoint } from "../../../models/apiEndpoints";
import { APIError } from "../../../models/exceptions";
import { ExceptionLayout } from "../ExceptionLayout";
import { CliCommand } from "../CliCommand";
import { BlobServiceClient } from "@azure/storage-blob";

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

  const apiCall = useAuthApiCall();

  const [uploadProgress, setUploadProgress] = useState<number>(0);

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

  const downloadFile = async () => {
    if (!sasUrl) return;

    const parsed = parseSasUrl(sasUrl);
    if (!parsed) {
      alert("Invalid SAS URL");
      return;
    }

    const { StorageAccountName, containerName, sasToken } = parsed;

    try {
      const blobServiceClient = new BlobServiceClient(
        `https://${StorageAccountName}.blob.core.windows.net/?${sasToken}`
      );

      const containerClient = blobServiceClient.getContainerClient(containerName);

      // Get first blob
      const blobIterator = containerClient.listBlobsFlat();
      const blobItem = (await blobIterator.next()).value;

      if (!blobItem?.name) {
        alert("No file found in container.");
        return;
      }

      const blobClient = containerClient.getBlobClient(blobItem.name);
      const blobUrl = blobClient.url;

      const res = await fetch(blobUrl);
      if (!res.ok) {
        alert("Failed to fetch file from blob storage.");
        return;
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = blobItem.name;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Download failed:", error);
      alert("Download failed. See console for details.");
    }
  };


  useEffect(() => {
    generateSasUrl();
  }, [generateSasUrl]);

  return (
    <Stack>
      <Pivot aria-label="Storage options">
        <PivotItem headerText="File Dialog">
          <Stack.Item style={{ paddingTop: "10px" }}>
            {props.request.status === AirlockRequestStatus.Draft ? (
              <>
                <input
                  type="file"
                  id="fileInput"
                  style={{ display: "none" }}
                  onChange={async (e) => {
                    const file = e.target.files?.[0];
                    if (!file || !sasUrl) return;

                    const parsed = parseSasUrl(sasUrl);
                    if (!parsed) return;

                    const { StorageAccountName, containerName, sasToken } = parsed;
                    const blobServiceClient = new BlobServiceClient(
                      `https://${StorageAccountName}.blob.core.windows.net/?${sasToken}`
                    );

                    const containerClient = blobServiceClient.getContainerClient(containerName);
                    const blockBlobClient = containerClient.getBlockBlobClient(file.name);

                    try {
                      await blockBlobClient.uploadBrowserData(file, {
                        blobHTTPHeaders: { blobContentType: file.type },
                        onProgress: (ev: { loadedBytes: number }) => {
                          const percent = (ev.loadedBytes / file.size) * 100;
                          console.log(`Progress: ${percent.toFixed(2)}%`);
                          setUploadProgress(percent);
                        },
                      });
                      alert("Upload complete!");
                      setTimeout(() => setUploadProgress(0), 1000);
                    } catch (err) {
                      console.error("Upload failed", err);
                      alert("Upload failed. See console for details.");
                      setTimeout(() => setUploadProgress(0), 1000);
                    }
                  }}
                />
                <PrimaryButton
                  text="Upload File"
                  onClick={() => document.getElementById("fileInput")?.click()}
                  disabled={!sasUrl}
                />
                {uploadProgress > 0 && uploadProgress < 100 && (
                  <ProgressIndicator
                    label="Uploading..."
                    percentComplete={uploadProgress / 100}
                  />
                )}
              </>
            ) : (
              <PrimaryButton
                text="Download File"
                onClick={downloadFile}
                disabled={!sasUrl}
              />
            )}
          </Stack.Item>
        </PivotItem>
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
      </Pivot>
      {sasUrlError && <ExceptionLayout e={apiSasUrlError} />}
    </Stack>
  );
};

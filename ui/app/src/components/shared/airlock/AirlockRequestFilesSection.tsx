import { MessageBar, MessageBarType, Pivot, PivotItem, PrimaryButton, Stack, TextField, } from "@fluentui/react";
import React, { useCallback, useEffect, useState } from "react";
import { HttpMethod, useAuthApiCall } from "../../../hooks/useAuthApiCall";
import { AirlockRequest, AirlockRequestStatus } from "../../../models/airlock";
import { ApiEndpoint } from "../../../models/apiEndpoints";
import { APIError } from "../../../models/exceptions";
import { ExceptionLayout } from "../ExceptionLayout";
import { CliCommand } from "../CliCommand";

interface AirlockRequestFilesSectionProps {
  request: AirlockRequest;
  workspaceApplicationIdURI: string;
}

export const AirlockRequestFilesSection: React.FunctionComponent<AirlockRequestFilesSectionProps> = (props: AirlockRequestFilesSectionProps) => {

  const [filesLink, setFilesLink] = useState<string>();
  const [cliCommand, setCliCommand] = useState<string>("");

  const [filesLinkError, setFilesLinkError] = useState(false);
  const [apiFilesLinkError, setApiFilesLinkError] = useState({} as APIError);
  const [cliCommandError, setCliCommandError] = useState(false);
  const [apiCliCommandError, setApiCliCommandError] = useState({} as APIError);


  const apiCall = useAuthApiCall();

  const parseSasUrl = (sasUrl: string) => {
    const match = sasUrl.match(/https:\/\/(.*?).blob.core.windows.net\/(.*)\?(.*)$/);
    if (!match) {
      return
    }

    return {
      StorageAccountName: match[1],
      containerName: match[2],
      sasToken: match[3]
    }
  }

  const generateFilesLink = useCallback(async () => {
    if (props.request && props.request.workspaceId) {
      try {
        const linkObject = await apiCall(
          `${ApiEndpoint.Workspaces}/${props.request.workspaceId}/${ApiEndpoint.AirlockRequests}/${props.request.id}/${ApiEndpoint.AirlockLink}`,
          HttpMethod.Get,
          props.workspaceApplicationIdURI
        );
        setFilesLink(linkObject.containerUrl);
      } catch (err: any) {
        err.userMessage = 'Error retrieving storage link';
        setApiFilesLinkError(err);
        setFilesLinkError(true);
      }
    }
  }, [apiCall, props.request, props.workspaceApplicationIdURI]);

  const generateAzureCliCommand = useCallback(async () => {
    if (props.request && props.request.workspaceId) {
      try {
        const linkObject = await apiCall(
          `${ApiEndpoint.Workspaces}/${props.request.workspaceId}/${ApiEndpoint.AirlockRequests}/${props.request.id}/${ApiEndpoint.AirlockLink}`,
          HttpMethod.Get,
          props.workspaceApplicationIdURI
        );

        let containerDetails = parseSasUrl(linkObject.containerUrl)
        if (!containerDetails) {
          return
        }

        let cliCommand = "";
        if (props.request.status === AirlockRequestStatus.Draft) {
          cliCommand = `az storage blob upload --file <~/path/to/file> --name <filename.filetype> --account-name ${containerDetails.StorageAccountName} --type block --container-name ${containerDetails.containerName} --sas-token "${containerDetails.sasToken}"`
        } else {
          cliCommand = `az storage blob download-batch --destination <~/destination/path/for/file> --source ${containerDetails.containerName} --account-name ${containerDetails.StorageAccountName} --sas-token "${containerDetails.sasToken}"`
        }

        setCliCommand(cliCommand);
      } catch (err: any) {
        err.userMessage = 'Error generating CLI command';
        setApiCliCommandError(err);
        setCliCommandError(true);
      }
    }
  }, [apiCall, props.request, props.workspaceApplicationIdURI]);

  useEffect(() => {
    generateAzureCliCommand()
  }, [generateAzureCliCommand]);

  return (
    <Pivot aria-label="Storage options">
      <PivotItem headerText="SAS URL">
        <Stack>
          <Stack.Item style={{ paddingTop: '10px', paddingBottom: '10px' }}>
            {
              props.request.status === AirlockRequestStatus.Draft
                ? <small>Generate a storage container SAS URL to upload your request file.</small>
                : <small>Generate a storage container SAS URL to view the request file.</small>
            }
            <Stack horizontal styles={{ root: { alignItems: 'center', paddingTop: '7px' } }}>
              <Stack.Item grow>
                <TextField readOnly value={filesLink} defaultValue="Click generate to create a link" />
              </Stack.Item>
              {
                filesLink ? <PrimaryButton
                  iconProps={{ iconName: 'copy' }}
                  styles={{ root: { minWidth: '40px' } }}
                  onClick={() => { navigator.clipboard.writeText(filesLink) }}
                /> : <PrimaryButton onClick={() => { setFilesLinkError(false); generateFilesLink() }}>Generate</PrimaryButton>
              }
            </Stack>
          </Stack.Item>
          {
            props.request.status === AirlockRequestStatus.Draft && <MessageBar messageBarType={MessageBarType.info}>
              Please upload a single file. Only single-file imports (including zip files) are supported.
            </MessageBar>
          }
          {
            filesLinkError && <ExceptionLayout e={apiFilesLinkError} />
          }
        </Stack>
      </PivotItem>
      <PivotItem headerText="CLI">
        <Stack>
          <Stack.Item style={{ paddingTop: '10px', paddingBottom: '10px' }}>
            <small>Use Azure command-line interface (Azure CLI) to interact with the storage container.</small>
            <hr style={{ border: "1px solid #faf9f8", borderRadius: "1px" }} />
          </Stack.Item>
          <Stack.Item style={{ paddingTop: '10px' }}>
            <CliCommand
              command={cliCommand}
              title={props.request.status === AirlockRequestStatus.Draft ? "Upload a file to the storage container" : "Download the file from the storage container"}
              isLoading={!cliCommand && !cliCommandError}
            />
          </Stack.Item>
          {
            cliCommandError && <ExceptionLayout e={apiCliCommandError} />
          }
        </Stack>
      </PivotItem>
    </Pivot>
  );
};

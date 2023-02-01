import { MessageBar, MessageBarType, Pivot, PivotItem, PrimaryButton, Stack, TextField } from "@fluentui/react";
import React, { useCallback, useState } from "react";
import { HttpMethod, useAuthApiCall } from "../../../hooks/useAuthApiCall";
import { AirlockRequest, AirlockRequestStatus } from "../../../models/airlock";
import { ApiEndpoint } from "../../../models/apiEndpoints";
import { APIError } from "../../../models/exceptions";
import { ExceptionLayout } from "../ExceptionLayout";

interface AirlockRequestFilesSectionProps {
  request: AirlockRequest;
  workspaceApplicationIdURI: string;
}

export const AirlockRequestFilesSection: React.FunctionComponent<AirlockRequestFilesSectionProps> = (props: AirlockRequestFilesSectionProps) => {
  const [filesLink, setFilesLink] = useState<string>();
  const [filesLinkError, setFilesLinkError] = useState(false);
  const [apiFilesLinkError, setApiFilesLinkError] = useState({} as APIError);
  const apiCall = useAuthApiCall();

  // Retrieve a link to view/edit the airlock files
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
        
      </PivotItem>
    </Pivot>
  );
};

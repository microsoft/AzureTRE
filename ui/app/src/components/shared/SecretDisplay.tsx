import { IconButton, Spinner, SpinnerSize, Stack, Text, TooltipHost } from "@fluentui/react";
import React, { useContext, useState } from "react";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { HttpMethod, useAuthApiCall } from "../../hooks/useAuthApiCall";
import { ApiEndpoint } from "../../models/apiEndpoints";
import { APIError } from "../../models/exceptions";
import { Resource } from "../../models/resource";
import { Secret } from "../../models/secret";
import { ExceptionLayout } from "./ExceptionLayout";

interface SecretDisplayProps {
  resource: Resource;
  propertyName: string;
}

// Displays a masked placeholder for a workspace Key Vault secret and lets the
// user reveal the value on demand. The secret value is only retrieved from the
// API when the user chooses to reveal it, and is never persisted.
export const SecretDisplay: React.FunctionComponent<SecretDisplayProps> = (props: SecretDisplayProps) => {
  const workspaceCtx = useContext(WorkspaceContext);
  const apiCall = useAuthApiCall();

  const [secretValue, setSecretValue] = useState<string | undefined>(undefined);
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<APIError | undefined>(undefined);

  const COPY_TOOL_TIP_DEFAULT_MESSAGE = "Copy to clipboard";
  const [copyToolTipMessage, setCopyToolTipMessage] = useState<string>(COPY_TOOL_TIP_DEFAULT_MESSAGE);

  const revealSecret = async () => {
    setIsLoading(true);
    setApiError(undefined);
    try {
      const secret: Secret = await apiCall(
        `${props.resource.resourcePath}/${ApiEndpoint.Secrets}/${props.propertyName}`,
        HttpMethod.Get,
        workspaceCtx.workspaceApplicationIdURI,
      );
      setSecretValue(secret.value);
    } catch (err: any) {
      err.userMessage = "Error retrieving secret";
      setApiError(err as APIError);
    }
    setIsLoading(false);
  };

  const hideSecret = () => {
    setSecretValue(undefined);
    setApiError(undefined);
  };

  const handleCopySecret = () => {
    if (secretValue === undefined) return;
    navigator.clipboard.writeText(secretValue);
    setCopyToolTipMessage("Copied");
    setTimeout(() => setCopyToolTipMessage(COPY_TOOL_TIP_DEFAULT_MESSAGE), 3000);
  };

  return (
    <>
      <Stack horizontal verticalAlign="center" tokens={{ childrenGap: 5 }}>
        <Stack.Item>
          {secretValue !== undefined ? (
            <code style={{ wordBreak: "break-all" }}>{secretValue}</code>
          ) : (
            <Text>••••••••</Text>
          )}
        </Stack.Item>
        {isLoading ? (
          <Spinner size={SpinnerSize.small} ariaLabel="Retrieving secret" />
        ) : secretValue !== undefined ? (
          <>
            <TooltipHost content="Hide secret">
              <IconButton iconProps={{ iconName: "Hide" }} ariaLabel="Hide secret" onClick={hideSecret} />
            </TooltipHost>
            <TooltipHost content={copyToolTipMessage}>
              <IconButton
                iconProps={{ iconName: "Copy" }}
                ariaLabel="Copy secret to clipboard"
                onClick={handleCopySecret}
              />
            </TooltipHost>
          </>
        ) : (
          <TooltipHost content="Show secret">
            <IconButton iconProps={{ iconName: "RedEye" }} ariaLabel="Show secret" onClick={revealSecret} />
          </TooltipHost>
        )}
      </Stack>
      {apiError && <ExceptionLayout e={apiError} />}
    </>
  );
};

import { ActionButton, getTheme, Link, mergeStyles, Spinner, SpinnerSize, Stack, Text } from "@fluentui/react";
import React, { useEffect, useContext, useState } from "react";
import { useParams } from "react-router-dom";
import { HttpMethod, useAuthApiCall } from "../../hooks/useAuthApiCall";
import { Operation, failedStates, inProgressStates } from "../../models/operation";
import { Resource } from "../../models/resource";
import { ApiEndpoint } from "../../models/apiEndpoints";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import config from "../../config.json";
import { APIError } from "../../models/exceptions";
import { LoadingState } from "../../models/loadingState";
import { ExceptionLayout } from "./ExceptionLayout";
import { ErrorPanel } from "./ErrorPanel";
import { ResourceOperationStepsList } from "./ResourceOperationStepsList";
import { RelativeTime, statusLabel, StatusIcon, userDisplayName } from "./ResourceDetailsLayout";

interface ResourceOperationsListProps {
  resource: Resource;
}

const theme = getTheme();

const rowClass = mergeStyles({
  borderBottom: `1px solid ${theme.palette.neutralLighter}`,
  padding: "12px 5px",
});

const mutedClass = mergeStyles({ color: theme.palette.neutralSecondary });

const capitalise = (s: string) => (s ? s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, " ") : s);

const OperationRow: React.FunctionComponent<{ op: Operation }> = ({ op }) => {
  const isFailed = failedStates.includes(op.status);
  const isActive = inProgressStates.includes(op.status);
  // Expand steps when there's something to look at: a failure or an operation still running.
  const [showSteps, setShowSteps] = useState(isFailed || isActive);
  const [showError, setShowError] = useState(false);
  const stepCount = op.steps?.length || 0;

  return (
    <Stack className={rowClass} tokens={{ childrenGap: 6 }}>
      <Stack horizontal verticalAlign="center" horizontalAlign="space-between" wrap tokens={{ childrenGap: 12 }}>
        <Stack horizontal verticalAlign="center" tokens={{ childrenGap: 10 }}>
          <StatusIcon status={op.status} />
          <Text styles={{ root: { fontWeight: 600 } }}>{capitalise(op.action)}</Text>
          <Text className={mutedClass}>{statusLabel(op.status)}</Text>
          <Text variant="small" className={mutedClass}>
            v{op.resourceVersion}
          </Text>
        </Stack>
        <Stack horizontal verticalAlign="center" tokens={{ childrenGap: 6 }} className={mutedClass}>
          <RelativeTime unixTime={op.updatedWhen || op.createdWhen} />
          <Text className={mutedClass}>by {userDisplayName(op.user)}</Text>
        </Stack>
      </Stack>
      {isFailed ? (
        <div>
          <Link onClick={() => setShowError(true)}>View error details</Link>
          <ErrorPanel errorMessage={op.message} isOpen={showError} onDismiss={() => setShowError(false)} />
        </div>
      ) : (
        op.message && (
          <Text variant="small" className={mutedClass} style={{ wordBreak: "break-word" }}>
            {op.message}
          </Text>
        )
      )}
      {stepCount > 0 && (
        <>
          <div>
            <ActionButton
              iconProps={{ iconName: showSteps ? "ChevronDown" : "ChevronRight" }}
              aria-expanded={showSteps}
              styles={{ root: { height: 24, padding: 0 } }}
              onClick={() => setShowSteps((s) => !s)}
            >
              {stepCount === 1 ? "1 step" : `${stepCount} steps`}
            </ActionButton>
          </div>
          {showSteps && (
            <div style={{ paddingLeft: 26 }}>
              <ResourceOperationStepsList steps={op.steps} />
            </div>
          )}
        </>
      )}
    </Stack>
  );
};

export const ResourceOperationsList: React.FunctionComponent<ResourceOperationsListProps> = (
  props: ResourceOperationsListProps,
) => {
  const apiCall = useAuthApiCall();
  const [apiError, setApiError] = useState({} as APIError);
  const workspaceCtx = useContext(WorkspaceContext);
  const { resourceId } = useParams();
  const [resourceOperations, setResourceOperations] = useState([] as Array<Operation>);
  const [loadingState, setLoadingState] = useState("loading");

  useEffect(() => {
    const getOperations = async () => {
      try {
        const scopeId =
          workspaceCtx.roles && workspaceCtx.roles.length > 0 ? workspaceCtx.workspaceApplicationIdURI : "";
        const ops = await apiCall(`${props.resource.resourcePath}/${ApiEndpoint.Operations}`, HttpMethod.Get, scopeId);
        config.debug && console.log(`Got resource operations, for resource:${props.resource.id}: ${ops.operations}`);
        setResourceOperations(ops.operations.reverse());
        setLoadingState(ops && ops.operations.length > 0 ? LoadingState.Ok : LoadingState.Error);
      } catch (err: any) {
        err.userMessage = "Error retrieving resource operations";
        setApiError(err);
        setLoadingState(LoadingState.Error);
      }
    };
    getOperations();
  }, [apiCall, props.resource, resourceId, workspaceCtx.roles, workspaceCtx.workspaceApplicationIdURI]);

  switch (loadingState) {
    case LoadingState.Ok:
      return (
        <Stack aria-label="Resource operations">
          {resourceOperations.map((op: Operation) => (
            <OperationRow key={op.id} op={op} />
          ))}
        </Stack>
      );
    case LoadingState.Error:
      return <ExceptionLayout e={apiError} />;
    default:
      return (
        <div style={{ marginTop: "20px" }}>
          <Spinner label="Loading operations" ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
        </div>
      );
  }
};

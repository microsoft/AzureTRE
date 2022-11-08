import { DefaultButton, DialogFooter, FontWeights, getTheme, IButtonStyles, IconButton, IIconProps, IStackItemStyles, IStackStyles, mergeStyleSets, MessageBar, MessageBarType, PrimaryButton, Shimmer, Spinner, SpinnerSize, Stack, TextField } from "@fluentui/react";
import { useCallback, useContext, useEffect, useState } from "react";
import { WorkspaceContext } from "../../../contexts/WorkspaceContext";
import { HttpMethod, useAuthApiCall } from "../../../hooks/useAuthApiCall";
import { AirlockRequest } from "../../../models/airlock";
import { ApiEndpoint } from "../../../models/apiEndpoints";
import { APIError } from "../../../models/exceptions";
import { destructiveButtonStyles, successButtonStyles } from "../../../styles";
import { ExceptionLayout } from "../ExceptionLayout";
import { UserResource } from '../../../models/userResource';
import { PowerStateBadge } from "../PowerStateBadge";
import { useComponentManager } from "../../../hooks/useComponentManager";
import { ComponentAction, Resource, VMPowerStates } from "../../../models/resource";
import { actionsDisabledStates, failedStates, inProgressStates, successStates } from "../../../models/operation";
import { useAppDispatch } from "../../../hooks/customReduxHooks";
import { addUpdateOperation } from "../notifications/operationsSlice";
import { StatusBadge } from "../StatusBadge";
import vmImage from "../../../assets/virtual_machine.svg";

interface AirlockReviewRequestProps {
  request: AirlockRequest | undefined,
  onUpdateRequest: (request: AirlockRequest) => void,
  onReviewRequest: (request: AirlockRequest) => void,
  onClose: () => void
}

export const AirlockReviewRequest: React.FunctionComponent<AirlockReviewRequestProps> = (props: AirlockReviewRequestProps) => {
  const [request, setRequest] = useState<AirlockRequest>();
  const [reviewExplanation, setReviewExplanation] = useState('');
  const [reviewing, setReviewing] = useState(false);
  const [reviewError, setReviewError] = useState(false);
  const [reviewResourcesConfigured, setReviewResourcesConfigured] = useState(false);
  const [reviewResourceStatus, setReviewResourceStatus] = useState<'notCreated' | 'creating' | 'created'>();
  const [reviewResourceError, setReviewResourceError] = useState(false);
  const [apiError, setApiError] = useState({} as APIError);
  const [proceedToReview, setProceedToReview] = useState(false);
  const [reviewResource, setReviewResource] = useState({} as UserResource);
  const [reviewWorkspaceScope, setReviewWorkspaceScope] = useState<string>();
  const workspaceCtx = useContext(WorkspaceContext);
  const apiCall = useAuthApiCall();
  const dispatch = useAppDispatch();

  useEffect(() => setRequest(props.request), [props.request]);

  // Check if Review Resources are configured for the current workspace
  useEffect(() => {
    if (
      request
      && workspaceCtx.workspace?.properties.airlock_review_config
      && workspaceCtx.workspace?.properties.airlock_review_config[request.type]
    ) {
      console.log('Setting review resources configured');
      setReviewResourcesConfigured(true);
    } else {
      setReviewResourcesConfigured(false);
    }
  }, [request, workspaceCtx]);

  // Get the review user resource if present in the airlock request
  useEffect(() => {
    const getReviewUserResource = async () => {
      setReviewResourceError(false);
      try {
        // TODO: support more than one resource
        const reviewWorkspaceId = request?.reviewUserResources[0].workspaceId;
        const reviewServiceId = request?.reviewUserResources[0].workspaceServiceId;
        const reviewResourceId = request?.reviewUserResources[0].userResourceId;

        // First fetch the scope for the review resource workspace if different to the airlock request workspace
        let scopeId;
        if (reviewWorkspaceId !== workspaceCtx.workspace.id) {
          scopeId = (await apiCall(`${ApiEndpoint.Workspaces}/${reviewWorkspaceId}/scopeid`, HttpMethod.Get)).workspaceAuth.scopeId;
          if (!scopeId) {
            throw Error("Unable to get scope_id from review resource workspace - authentication not set up.");
          }
        } else {
          scopeId = workspaceCtx.workspaceApplicationIdURI;
        }
        setReviewWorkspaceScope(scopeId);

        // Get the review user resource
        const resource = (await apiCall(
          `${ApiEndpoint.Workspaces}/${reviewWorkspaceId}/${ApiEndpoint.WorkspaceServices}/${reviewServiceId}/${ApiEndpoint.UserResources}/${reviewResourceId}`,
          HttpMethod.Get,
          scopeId
        )).userResource;
        setReviewResource(resource);
      } catch (err: any) {
        err.userMessage = "Error retrieving resource";
        setApiError(err);
        setReviewResourceError(true);
      }
    };
    if (reviewResourcesConfigured && request?.reviewUserResources && request?.reviewUserResources.length > 0) {
      getReviewUserResource();
    }
  }, [apiCall, request, workspaceCtx.workspace.id, workspaceCtx.workspaceApplicationIdURI, reviewResourcesConfigured]);

  // Get the latest updates to the review resource to track deployment
  const latestUpdate = useComponentManager(
    reviewResource,
    (r: Resource) => { setReviewResource(r as UserResource) },
    () => { setReviewResource({} as UserResource) },
    reviewWorkspaceScope // Pass this so component manager knows it might be different to the workspace context
  );

  // Set the review resource status
  useEffect(() => {
    if (inProgressStates.includes(latestUpdate.operation?.status) || inProgressStates.includes(reviewResource.deploymentStatus)) {
      setReviewResourceStatus('creating');
    } else if (failedStates.includes(latestUpdate.operation?.status) || failedStates.includes(reviewResource.deploymentStatus)) {
      setReviewResourceStatus('notCreated');
      const err = new Error(latestUpdate.operation?.message) as any;
      err.userMessage = 'An issue occurred while deploying the review resource.'
      setApiError(new Error(latestUpdate.operation?.message));
      setReviewResourceError(true);
    } else if (successStates.includes(latestUpdate.operation?.status) || successStates.includes(reviewResource.deploymentStatus)) {
      setReviewResourceStatus('created');
    } else if (request && request.reviewUserResources?.length === 0) {
      setReviewResourceStatus('notCreated');
    }
  }, [latestUpdate.operation, reviewResource.deploymentStatus, request])

  // Create a review resource
  const createReviewResource = useCallback(async () => {
    setReviewResourceError(false);
    setReviewResourceStatus('creating');
    try {
      const response = await apiCall(
        `${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.AirlockRequests}/${request?.id}/${ApiEndpoint.AirlockCreateReviewResource}`,
        HttpMethod.Post,
        workspaceCtx.workspaceApplicationIdURI
      );
      dispatch(addUpdateOperation(response.operation));
      props.onUpdateRequest(response.airlockRequest);
    } catch (err: any) {
      err.userMessage = "Error creating review resource";
      setApiError(err);
      setReviewResourceError(true);
      setReviewResourceStatus('notCreated');
    }
  }, [apiCall, workspaceCtx.workspaceApplicationIdURI, request?.id, workspaceCtx.workspace.id, dispatch, props])

  // Review an airlock request
  const reviewRequest = useCallback(async (isApproved: boolean) => {
    if (request && reviewExplanation) {
      setReviewing(true);
      setReviewError(false);
      try {
        const review = {
          approval: isApproved,
          decisionExplanation: reviewExplanation
        };
        const response = await apiCall(
          `${ApiEndpoint.Workspaces}/${request.workspaceId}/${ApiEndpoint.AirlockRequests}/${request.id}/${ApiEndpoint.AirlockReview}`,
          HttpMethod.Post,
          workspaceCtx.workspaceApplicationIdURI,
          review
        );
        props.onReviewRequest(response.airlockRequest);
      } catch (err: any) {
        err.userMessage = 'Error reviewing airlock request';
        setApiError(err);
        setReviewError(true);
      }
      setReviewing(false);
    }
  }, [apiCall, request, workspaceCtx.workspaceApplicationIdURI, reviewExplanation, props]);

  // Get connection properies for review userResource
  let connectUri: string;
  if (reviewResource?.properties && reviewResource.properties.connection_uri) {
    connectUri = reviewResource.properties.connection_uri;
  }

  // Determine whether or not to disable the connect button
  const connectDisabled = () => {
    return latestUpdate.componentAction === ComponentAction.Lock
      || actionsDisabledStates.includes(reviewResource.deploymentStatus)
      || !reviewResource.isEnabled
      || (reviewResource.azureStatus?.powerState && reviewResource.azureStatus.powerState !== VMPowerStates.Running)
      || !connectUri
  }

  let statusBadge = <Shimmer></Shimmer>;
  let action = <Spinner style={{marginRight:20}}></Spinner>;

  // Determine the relevant actions and status to show
  switch (reviewResourceStatus) {
    case 'creating':
      statusBadge = <StatusBadge
        resource={reviewResource}
        status={latestUpdate.operation?.status}
      />;
      break;
    case 'notCreated':
      statusBadge = <small>Not created</small>;
      action = <PrimaryButton onClick={createReviewResource} text="Create" />;
      break;
    case 'created':
      statusBadge = <PowerStateBadge state={reviewResource?.azureStatus.powerState} />;
      action = <PrimaryButton
        onClick={() => window.open(connectUri)}
        text="View data"
        disabled={connectDisabled()}
        title={connectDisabled() ? 'Resource must be enabled, successfully deployed & powered on to connect' : 'Connect to resource'}
      />;
      break;
  }

  const currentStep = !proceedToReview ? <>
    <p>
      To securely review the request's data, you need to create a review VM. Click "Create" and a VM will be created with the data
      automatically downloaded onto it. Once you've viewed the data, click "Proceed to review" to make your decision.
    </p>
    {
      reviewResourcesConfigured ? <> {
        !reviewResourceError ? <Stack horizontal horizontalAlign="space-between" styles={reviewVMStyles}>
          <Stack.Item styles={reviewVMItemStyles}>
            <img src={vmImage} alt="Virtual machine" width="50" />
            <div style={{marginLeft:20}}>
              <h3 style={{marginTop:0, marginBottom:2}}>Review VM</h3>
              { statusBadge }
            </div>
          </Stack.Item>
          <Stack.Item styles={reviewVMItemStyles}>
            { action }
          </Stack.Item>
        </Stack> : <ExceptionLayout e={apiError} />
      } </> : <>
        <MessageBar messageBarType={MessageBarType.severeWarning}>
          It looks like review VMs aren't set up in your workspace. Please contact your Workspace Owner.
        </MessageBar>
      </>
    }
    <DialogFooter>
      <DefaultButton onClick={props.onClose} text="Cancel" />
      <PrimaryButton onClick={() => setProceedToReview(true)} text="Proceed to review" />
    </DialogFooter>
  </> : <>
    <TextField
      label="Reason for decision"
      placeholder="Please provide a brief explanation of your decision."
      value={reviewExplanation}
      onChange={(e: React.FormEvent, newValue?: string) => setReviewExplanation(newValue || '')}
      multiline
      rows={6}
      required
    />
    {
      reviewError && <ExceptionLayout e={apiError} />
    }
    {
      reviewing
      ? <Spinner label="Submitting review..." ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} style={{marginTop:20}} />
      : <DialogFooter>
        <DefaultButton
          onClick={() => setProceedToReview(false)}
          text="Back"
          styles={{root:{float:'left'}}}
        />
        <DefaultButton
          iconProps={{iconName: 'Cancel'}}
          onClick={() => reviewRequest(false)}
          text="Reject"
          styles={destructiveButtonStyles}
          disabled={reviewExplanation.length <= 0}
        />
        <DefaultButton
          iconProps={{iconName: 'Accept'}}
          onClick={() => reviewRequest(true)}
          text="Approve"
          styles={successButtonStyles}
          disabled={reviewExplanation.length <= 0}
        />
      </DialogFooter>
    }
  </>

  return (
    <>
      <div className={contentStyles.header}>
        <span id={`title-${request?.id}`}>Review: {request?.title}</span>
        <IconButton
          styles={iconButtonStyles}
          iconProps={cancelIcon}
          ariaLabel="Close popup modal"
          onClick={props.onClose}
        />
      </div>
      <div className={contentStyles.body}>
        { currentStep }
      </div>
    </>
  )
}

const theme = getTheme();
const contentStyles = mergeStyleSets({
  header: [
    theme.fonts.xLarge,
    {
      flex: '1 1 auto',
      borderTop: `4px solid ${theme.palette.themePrimary}`,
      color: theme.palette.neutralPrimary,
      display: 'flex',
      alignItems: 'center',
      fontWeight: FontWeights.semibold,
      padding: '12px 12px 14px 24px',
    },
  ],
  body: {
    flex: '4 4 auto',
    padding: '0 24px 24px 24px',
    overflowY: 'hidden',
    selectors: {
      p: { margin: '14px 0' },
      'p:first-child': { marginTop: 0 },
      'p:last-child': { marginBottom: 0 },
    },
    width: 600
  },
});

const iconButtonStyles: Partial<IButtonStyles> = {
  root: {
    color: theme.palette.neutralPrimary,
    marginLeft: 'auto',
    marginTop: '4px',
    marginRight: '2px',
  },
  rootHovered: {
    color: theme.palette.neutralDark,
  },
};

const cancelIcon: IIconProps = { iconName: 'Cancel' };

const reviewVMStyles: IStackStyles = {
  root:{
    marginTop: 20,
    marginBottom: 20,
    padding: 20,
    backgroundColor: theme.palette.neutralLighter
  }
};

const reviewVMItemStyles: IStackItemStyles = {
  root: {
    display:'flex',
    alignItems:'center'
  }
}

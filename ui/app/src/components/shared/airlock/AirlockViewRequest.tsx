import { DefaultButton, Dialog, DialogFooter, IStackItemStyles, IStackStyles, MessageBar, Panel, PanelType, Persona, PersonaSize, PrimaryButton, Spinner, SpinnerSize, Stack, TextField, useTheme } from "@fluentui/react";
import moment from "moment";
import { useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { WorkspaceContext } from "../../../contexts/WorkspaceContext";
import { HttpMethod, useAuthApiCall } from "../../../hooks/useAuthApiCall";
import { AirlockRequest, AirlockRequestStatus } from "../../../models/airlock";
import { ApiEndpoint } from "../../../models/apiEndpoints";
import { APIError } from "../../../models/exceptions";
import { ExceptionLayout } from "../ExceptionLayout";

interface AirlockViewRequestProps {
  requests: AirlockRequest[];
  updateRequest: (requests: AirlockRequest) => void;
}

const underlineStackStyles: IStackStyles = {
  root: {
    borderBottom: '#f2f2f2 solid 1px'
  },
};

const stackItemStyles: IStackItemStyles = {
  root: {
    alignItems: 'center',
    display: 'flex',
    height: 50,
    margin: '0px 5px'
  },
};

export const AirlockViewRequest: React.FunctionComponent<AirlockViewRequestProps> = (props: AirlockViewRequestProps) => {
  const {requestId} = useParams();
  const [request, setRequest] = useState<AirlockRequest>();
  const [filesLink, setFilesLink] = useState<string>();
  const [filesLinkError, setFilesLinkError] = useState(false);
  const [hideSubmitDialog, setHideSubmitDialog] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [cancelError, setCancelError] = useState(false);
  const [hideCancelDialog, setHideCancelDialog] = useState(true);
  const workspaceCtx = useContext(WorkspaceContext);
  const apiCall = useAuthApiCall();
  const [apiFilesLinkError, setApiFilesLinkError] = useState({} as APIError);
  const [apiSubmitError, setApiSubmitError] = useState({} as APIError);
  const [apiCancelError, setApiCancelError] = useState({} as APIError);
  const navigate = useNavigate();
  const theme = useTheme();

  const cancelButtonStyles = useMemo(() => ({
    root: {
      marginRight: 8,
      background: theme.palette.red,
      color: theme.palette.white,
      borderColor: theme.palette.red
    }
  }), [theme]);

  useEffect(() => {
    // Get the selected request from the router param and find in the requests prop
    const req = props.requests.find(r => r.id === requestId) as AirlockRequest;
    setRequest(req);
  }, [requestId, props.requests]);

  const generateFilesLink = useCallback(async () => {
    // Retrieve a link to view/edit the airlock files
    if (request && request.workspaceId) {
      try {
        const linkObject = await apiCall(
          `${ApiEndpoint.Workspaces}/${request.workspaceId}/${ApiEndpoint.AirlockRequests}/${request.id}/${ApiEndpoint.AirlockLink}`,
          HttpMethod.Get,
          workspaceCtx.workspaceApplicationIdURI
        );
        setFilesLink(linkObject.containerUrl);
      } catch (err: any) {
        err.userMessage = 'Error retrieving storage link';
        setApiFilesLinkError(err);
        setFilesLinkError(true);
      }
    }
  }, [apiCall, request, workspaceCtx.workspaceApplicationIdURI]);

  const dismissPanel = useCallback(() => navigate('../'), [navigate]);

  const submitRequest = useCallback(async () => {
    // Submit an airlock request
    if (request && request.workspaceId) {
      setSubmitting(true);
      setSubmitError(false);
      try {
        const response = await apiCall(
          `${ApiEndpoint.Workspaces}/${request.workspaceId}/${ApiEndpoint.AirlockRequests}/${request.id}/${ApiEndpoint.AirlockSubmit}`,
          HttpMethod.Post,
          workspaceCtx.workspaceApplicationIdURI
        );
        props.updateRequest(response.airlockRequest);
        setHideSubmitDialog(true);
      } catch (err: any) {
        err.userMessage = 'Error submitting airlock request';
        setApiSubmitError(err);
        setSubmitError(true);
      }
      setSubmitting(false);
    }
  }, [apiCall, request, props, workspaceCtx.workspaceApplicationIdURI]);

  const cancelRequest = useCallback(async () => {
    // Cancel an airlock request
    if (request && request.workspaceId) {
      setCancelling(true);
      setCancelError(false);
      try {
        const response = await apiCall(
          `${ApiEndpoint.Workspaces}/${request.workspaceId}/${ApiEndpoint.AirlockRequests}/${request.id}/${ApiEndpoint.AirlockCancel}`,
          HttpMethod.Post,
          workspaceCtx.workspaceApplicationIdURI
        );
        props.updateRequest(response.airlockRequest);
        setHideCancelDialog(true);
      } catch (err: any) {
        err.userMessage = 'Error cancelling airlock request';
        setApiCancelError(err);
        setCancelError(true);

      }
      setCancelling(false);
    }
  }, [apiCall, request, props, workspaceCtx.workspaceApplicationIdURI]);

  const renderFooter = useCallback(() => {
    let footer = <></>
    if (request) {
      footer = <>
        {
          request.status === AirlockRequestStatus.Draft && <div style={{marginTop: '10px', marginBottom: '10px'}}>
            <MessageBar>
              This request is currently in draft. Add a file to the request's storage container using the SAS URL and submit when ready.
            </MessageBar>
          </div>
        }
        <div style={{textAlign: 'end'}}>
          {
            request.status !== AirlockRequestStatus.Cancelled && <DefaultButton onClick={() => {setCancelError(false); setHideCancelDialog(false)}} styles={cancelButtonStyles}>Cancel Request</DefaultButton>
          }
          {
            request.status === AirlockRequestStatus.Draft && <PrimaryButton onClick={() => {setSubmitError(false); setHideSubmitDialog(false)}}>Submit</PrimaryButton>
          }
        </div>
      </>
    }
    return footer;
  }, [request, cancelButtonStyles]);

  return (
    <>
      <Panel
        headerText="View Airlock Request"
        isOpen={true}
        isLightDismiss={true}
        onDismiss={dismissPanel}
        onRenderFooterContent={renderFooter}
        isFooterAtBottom={true}
        closeButtonAriaLabel="Close"
        type={PanelType.custom}
        customWidth="450px"
      > {
        request ? <>
          <Stack horizontal horizontalAlign="space-between" style={{marginTop: '40px'}} styles={underlineStackStyles}>
            <Stack.Item styles={stackItemStyles}>
              <b>Initiator</b>
            </Stack.Item>
            <Stack.Item styles={stackItemStyles}>
              <Persona text={request.user.name} size={PersonaSize.size32} />
            </Stack.Item>
          </Stack>

          <Stack horizontal horizontalAlign="space-between" styles={underlineStackStyles}>
            <Stack.Item styles={stackItemStyles}>
              <b>Type</b>
            </Stack.Item>
            <Stack.Item styles={stackItemStyles}>
              <p>{request.requestType}</p>
            </Stack.Item>
          </Stack>

          <Stack horizontal horizontalAlign="space-between" styles={underlineStackStyles}>
            <Stack.Item styles={stackItemStyles}>
              <b>Status</b>
            </Stack.Item>
            <Stack.Item styles={stackItemStyles}>
              <p>{request.status}</p>
            </Stack.Item>
          </Stack>

          <Stack horizontal horizontalAlign="space-between" styles={underlineStackStyles}>
            <Stack.Item styles={stackItemStyles}>
              <b>Workspace</b>
            </Stack.Item>
            <Stack.Item styles={stackItemStyles}>
              <p>{workspaceCtx.workspace?.properties?.display_name}</p>
            </Stack.Item>
          </Stack>

          <Stack horizontal horizontalAlign="space-between" styles={underlineStackStyles}>
            <Stack.Item styles={stackItemStyles}>
              <b>Created</b>
            </Stack.Item>
            <Stack.Item styles={stackItemStyles}>
              <p>{moment.unix(request.creationTime).format('DD/MM/YYYY')}</p>
            </Stack.Item>
          </Stack>

          <Stack horizontal horizontalAlign="space-between" styles={underlineStackStyles}>
            <Stack.Item styles={stackItemStyles}>
              <b>Updated</b>
            </Stack.Item>
            <Stack.Item styles={stackItemStyles}>
              <p>{moment.unix(request.updatedWhen).fromNow()}</p>
            </Stack.Item>
          </Stack>

          <Stack style={{marginTop: '20px'}} styles={underlineStackStyles}>
            <Stack.Item styles={stackItemStyles}>
              <b>Business Justification</b>
            </Stack.Item>
          </Stack>
          <Stack>
            <Stack.Item styles={stackItemStyles}>
              <p>{request.businessJustification}</p>
            </Stack.Item>
          </Stack>

          <Stack style={{marginTop: '20px'}} styles={underlineStackStyles}>
            <Stack.Item styles={stackItemStyles}>
              <b>Files</b>
            </Stack.Item>
          </Stack>
          <Stack>
            <Stack.Item style={{paddingTop: '10px', paddingBottom: '10px'}}>
              <small>Generate a storage container SAS URL to view/modify the request file(s).</small>
              <Stack horizontal styles={{root: {alignItems: 'center', paddingTop: '7px'}}}>
                <Stack.Item grow>
                  <TextField readOnly value={filesLink} defaultValue="Click generate to create a link" />
                </Stack.Item>
                {
                  filesLink ? <PrimaryButton
                    iconProps={{iconName: 'copy'}}
                    styles={{root: {minWidth: '40px'}}}
                    onClick={() => {navigator.clipboard.writeText(filesLink)}}
                  /> : <PrimaryButton onClick={() => {setFilesLinkError(false); generateFilesLink()}}>Generate</PrimaryButton>
                }
              </Stack>
            </Stack.Item>
            {
              filesLinkError && <ExceptionLayout e={apiFilesLinkError} />
            }
          </Stack>
        </>
        : <div style={{ marginTop: '70px' }}>
          <Spinner label="Loading..." ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
        </div>
      }
        <Dialog
          hidden={hideSubmitDialog}
          onDismiss={() => setHideSubmitDialog(true)}
          dialogContentProps={{
            title: 'Submit request?',
            subText: 'Are you sure you want to submit this request for review?',
          }}
        >
          {
            submitError && <ExceptionLayout e={apiSubmitError} />
          }
          {
            submitting
            ? <Spinner label="Submitting..." ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
            : <DialogFooter>
              <PrimaryButton onClick={submitRequest} text="Submit" />
              <DefaultButton onClick={() => setHideSubmitDialog(true)} text="Cancel" />
            </DialogFooter>
          }
        </Dialog>

        <Dialog
          hidden={hideCancelDialog}
          onDismiss={() => setHideCancelDialog(true)}
          dialogContentProps={{
            title: 'Cancel Airlock Request?',
            subText: 'Are you sure you want to cancel this airlock request?',
          }}
        >
          {
            cancelError && <ExceptionLayout e={apiCancelError} />
          }
          {
            cancelling
            ? <Spinner label="Cancelling..." ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
            : <DialogFooter>
              <PrimaryButton onClick={cancelRequest} text="Cancel Request" styles={cancelButtonStyles} />
              <DefaultButton onClick={() => setHideCancelDialog(true)} text="Back" />
            </DialogFooter>
          }
        </Dialog>
      </Panel>
    </>
  )
}

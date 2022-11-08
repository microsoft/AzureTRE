import { DefaultButton, Dialog, DialogFooter, DocumentCard, DocumentCardActivity, DocumentCardDetails, DocumentCardTitle, DocumentCardType, FontIcon, getTheme, IStackItemStyles, IStackStyles, IStackTokens, mergeStyles, MessageBar, MessageBarType, Modal, Panel, PanelType, Persona, PersonaSize, PrimaryButton, Spinner, SpinnerSize, Stack, TextField } from "@fluentui/react";
import moment from "moment";
import React, { useCallback, useContext, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { WorkspaceContext } from "../../../contexts/WorkspaceContext";
import { HttpMethod, useAuthApiCall } from "../../../hooks/useAuthApiCall";
import { AirlockFilesLinkInvalidStatus, AirlockRequest, AirlockRequestAction, AirlockRequestStatus, AirlockReviewDecision } from "../../../models/airlock";
import { ApiEndpoint } from "../../../models/apiEndpoints";
import { APIError } from "../../../models/exceptions";
import { destructiveButtonStyles } from "../../../styles";
import { ExceptionLayout } from "../ExceptionLayout";
import { AirlockReviewRequest } from "./AirlockReviewRequest";

interface AirlockViewRequestProps {
  requests: AirlockRequest[];
  onUpdateRequest: (requests: AirlockRequest) => void;
}

export const AirlockViewRequest: React.FunctionComponent<AirlockViewRequestProps> = (props: AirlockViewRequestProps) => {
  const {requestId} = useParams();
  const [request, setRequest] = useState<AirlockRequest>();
  const [filesLink, setFilesLink] = useState<string>();
  const [filesLinkError, setFilesLinkError] = useState(false);
  const [hideSubmitDialog, setHideSubmitDialog] = useState(true);
  const [reviewIsOpen, setReviewIsOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(false);
  const [hideCancelDialog, setHideCancelDialog] = useState(true);
  const [apiFilesLinkError, setApiFilesLinkError] = useState({} as APIError);
  const [apiError, setApiError] = useState({} as APIError);
  const workspaceCtx = useContext(WorkspaceContext);
  const apiCall = useAuthApiCall();
  const navigate = useNavigate();

  useEffect(() => {
    // Get the selected request from the router param and find in the requests prop
    let req = props.requests.find(r => r.id === requestId) as AirlockRequest;

    // If not found, fetch it from the API
    if (!req) {
      apiCall(
        `${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.AirlockRequests}/${requestId}`,
        HttpMethod.Get,
        workspaceCtx.workspaceApplicationIdURI
      ).then((result) => {
        const request = result.airlockRequest as AirlockRequest;
        request.allowedUserActions = result.allowedUserActions;
        setRequest(request);
      });
    } else {
      setRequest(req);
    }
    console.log(req);
  }, [apiCall, requestId, props.requests, workspaceCtx.workspace.id, workspaceCtx.workspaceApplicationIdURI]);

  // Retrieve a link to view/edit the airlock files
  const generateFilesLink = useCallback(async () => {
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

  // Submit an airlock request
  const submitRequest = useCallback(async () => {
    if (request && request.workspaceId) {
      setSubmitting(true);
      setSubmitError(false);
      try {
        const response = await apiCall(
          `${ApiEndpoint.Workspaces}/${request.workspaceId}/${ApiEndpoint.AirlockRequests}/${request.id}/${ApiEndpoint.AirlockSubmit}`,
          HttpMethod.Post,
          workspaceCtx.workspaceApplicationIdURI
        );
        props.onUpdateRequest(response.airlockRequest);
        setHideSubmitDialog(true);
      } catch (err: any) {
        err.userMessage = 'Error submitting airlock request';
        setApiError(err);
        setSubmitError(true);
      }
      setSubmitting(false);
    }
  }, [apiCall, request, props, workspaceCtx.workspaceApplicationIdURI]);

  // Cancel an airlock request
  const cancelRequest = useCallback(async () => {
    if (request && request.workspaceId) {
      setSubmitting(true);
      setSubmitError(false);
      try {
        const response = await apiCall(
          `${ApiEndpoint.Workspaces}/${request.workspaceId}/${ApiEndpoint.AirlockRequests}/${request.id}/${ApiEndpoint.AirlockCancel}`,
          HttpMethod.Post,
          workspaceCtx.workspaceApplicationIdURI
        );
        props.onUpdateRequest(response.airlockRequest);
        setHideCancelDialog(true);
      } catch (err: any) {
        err.userMessage = 'Error cancelling airlock request';
        setApiError(err);
        setSubmitError(true);
      }
      setSubmitting(false);
    }
  }, [apiCall, request, props, workspaceCtx.workspaceApplicationIdURI]);

  // Render the panel footer along with buttons that the signed-in user is allowed to see according to the API
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
        {
          request.statusMessage && <div style={{marginTop: '10px', marginBottom: '10px'}}>
            <MessageBar messageBarType={MessageBarType.error}>{request.statusMessage}</MessageBar>
          </div>
        }
        <div style={{textAlign: 'end'}}>
          {
            request.allowedUserActions?.includes(AirlockRequestAction.Cancel) &&
              <DefaultButton onClick={() => {setSubmitError(false); setHideCancelDialog(false)}} styles={destructiveButtonStyles}>Cancel request</DefaultButton>
          }
          {
            request.allowedUserActions?.includes(AirlockRequestAction.Submit) &&
              <PrimaryButton onClick={() => {setSubmitError(false); setHideSubmitDialog(false)}}>Submit</PrimaryButton>
          }
          {
            request.allowedUserActions?.includes(AirlockRequestAction.Review) &&
              <PrimaryButton onClick={() => setReviewIsOpen(true)}>Review</PrimaryButton>
          }
        </div>
      </>
    }
    return footer;
  }, [request]);

  return (
    <>
      <Panel
        headerText={request && request.title ? request.title : "View airlock request"}
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
              <b>Id</b>
            </Stack.Item>
            <Stack.Item styles={stackItemStyles}>
            <p>{request.id}</p>
            </Stack.Item>
          </Stack>

          <Stack horizontal horizontalAlign="space-between" styles={underlineStackStyles}>
            <Stack.Item styles={stackItemStyles}>
              <b>Creator</b>
            </Stack.Item>
            <Stack.Item styles={stackItemStyles}>
              <Persona size={PersonaSize.size32} text={request.createdBy?.name} />
            </Stack.Item>
          </Stack>

          <Stack horizontal horizontalAlign="space-between" styles={underlineStackStyles}>
            <Stack.Item styles={stackItemStyles}>
              <b>Type</b>
            </Stack.Item>
            <Stack.Item styles={stackItemStyles}>
              <p>{request.type}</p>
            </Stack.Item>
          </Stack>

          <Stack horizontal horizontalAlign="space-between" styles={underlineStackStyles}>
            <Stack.Item styles={stackItemStyles}>
              <b>Status</b>
            </Stack.Item>
            <Stack.Item styles={stackItemStyles}>
              <p>{request.status.replace("_", " ")}</p>
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
              <p>{moment.unix(request.createdWhen).format('DD/MM/YYYY')}</p>
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
          {
            !AirlockFilesLinkInvalidStatus.includes(request.status) && <>
              <Stack style={{marginTop: '20px'}} styles={underlineStackStyles}>
                <Stack.Item styles={stackItemStyles}>
                  <b>Files</b>
                </Stack.Item>
              </Stack>
              <Stack>
                <Stack.Item style={{paddingTop: '10px', paddingBottom: '10px'}}>
                  {
                    request.status === AirlockRequestStatus.Draft
                      ? <small>Generate a storage container SAS URL to upload your request file.</small>
                      : <small>Generate a storage container SAS URL to view the request file.</small>
                  }
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
                  request.status === AirlockRequestStatus.Draft && <MessageBar messageBarType={MessageBarType.info}>
                    Please upload a single file. Only single-file imports (including zip files) are supported.
                  </MessageBar>
                }
                {
                  filesLinkError && <ExceptionLayout e={apiFilesLinkError} />
                }
              </Stack>
            </>
          }
          {
            request.reviews && request.reviews.length > 0 && <>
              <Stack style={{marginTop: '20px', marginBottom: '20px'}} styles={underlineStackStyles}>
                <Stack.Item styles={stackItemStyles}>
                  <b>Reviews</b>
                </Stack.Item>
              </Stack>
              <Stack tokens={stackTokens}>
                {
                  request.reviews.map((review, i) => {
                    return <DocumentCard
                      key={i}
                      aria-label="Review"
                      type={DocumentCardType.compact}>
                      <DocumentCardDetails>
                        <DocumentCardActivity
                          activity={moment.unix(review.dateCreated).fromNow()}
                          people={[{name: review.reviewer.name, profileImageSrc: ''}]}
                        />
                        <DocumentCardTitle
                          title={review.decisionExplanation}
                          shouldTruncate
                          showAsSecondaryTitle
                        />
                      </DocumentCardDetails>
                      <div style={{margin:10}}>
                        {
                          review.reviewDecision === AirlockReviewDecision.Approved && <>
                            <FontIcon aria-label="Approved" iconName="Completed" className={approvedIcon} />
                            Approved
                          </>
                        }
                        {
                          review.reviewDecision === AirlockReviewDecision.Rejected && <>
                            <FontIcon aria-label="Rejected" iconName="ErrorBadge" className={rejectedIcon} />
                            Rejected
                          </>
                        }
                      </div>
                    </DocumentCard>
                  })
                }
              </Stack>
            </>
          }
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
            subText: 'Make sure you have uploaded your file to the request\'s storage account before submitting.',
          }}
        >
          {
            submitError && <ExceptionLayout e={apiError} />
          }
          {
            submitting
            ? <Spinner label="Submitting..." ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
            : <DialogFooter>
              <DefaultButton onClick={() => setHideSubmitDialog(true)} text="Cancel" />
              <PrimaryButton onClick={submitRequest} text="Submit" />
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
            submitError && <ExceptionLayout e={apiError} />
          }
          {
            submitting
            ? <Spinner label="Cancelling..." ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
            : <DialogFooter>
              <DefaultButton onClick={cancelRequest} text="Cancel Request" styles={destructiveButtonStyles} />
              <DefaultButton onClick={() => setHideCancelDialog(true)} text="Back" />
            </DialogFooter>
          }
        </Dialog>

        <Modal
          titleAriaId={`title-${request?.id}`}
          isOpen={reviewIsOpen}
          onDismiss={() => setReviewIsOpen(false)}
          containerClassName={modalStyles}
        >
          <AirlockReviewRequest
            request={request}
            onUpdateRequest={props.onUpdateRequest}
            onReviewRequest={(request) => {props.onUpdateRequest(request); setReviewIsOpen(false)}}
            onClose={() => setReviewIsOpen(false)}
          />
        </Modal>
      </Panel>
    </>
  )
}

const { palette } = getTheme();
const stackTokens: IStackTokens = { childrenGap: 20 };

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

const approvedIcon = mergeStyles({
  color: palette.green,
  marginRight: 5,
  fontSize: 12
});

const rejectedIcon = mergeStyles({
  color: palette.red,
  marginRight: 5,
  fontSize: 12
});

const modalStyles = mergeStyles({
  display: 'flex',
  flexFlow: 'column nowrap',
  alignItems: 'stretch',
});

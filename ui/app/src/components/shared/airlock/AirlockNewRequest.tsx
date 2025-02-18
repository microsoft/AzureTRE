import {
  DefaultButton,
  Dialog,
  DialogFooter,
  DocumentCard,
  DocumentCardDetails,
  DocumentCardPreview,
  DocumentCardTitle,
  DocumentCardType,
  getTheme,
  Icon,
  IDocumentCardPreviewProps,
  IStackTokens,
  Panel,
  PanelType,
  PrimaryButton,
  Spinner,
  SpinnerSize,
  Stack,
  TextField,
} from "@fluentui/react";
import { useCallback, useContext, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { WorkspaceContext } from "../../../contexts/WorkspaceContext";
import { HttpMethod, useAuthApiCall } from "../../../hooks/useAuthApiCall";
import {
  AirlockRequest,
  AirlockRequestType,
  NewAirlockRequest,
} from "../../../models/airlock";
import { ApiEndpoint } from "../../../models/apiEndpoints";
import { APIError } from "../../../models/exceptions";
import { ExceptionLayout } from "../ExceptionLayout";

interface AirlockNewRequestProps {
  onCreateRequest: (request: AirlockRequest) => void;
}

export const AirlockNewRequest: React.FunctionComponent<
  AirlockNewRequestProps
> = (props: AirlockNewRequestProps) => {
  const [newRequest, setNewRequest] = useState<NewAirlockRequest>(
    {} as NewAirlockRequest,
  );
  const [requestValid, setRequestValid] = useState(false);
  const [hideCreateDialog, setHideCreateDialog] = useState(true);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState(false);
  const [apiCreateError, setApiSubmitError] = useState({} as APIError);
  const navigate = useNavigate();
  const workspaceCtx = useContext(WorkspaceContext);
  const apiCall = useAuthApiCall();

  const onChangetitle = useCallback(
    (
      event: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>,
      newValue?: string,
    ) => {
      setNewRequest((request) => {
        return {
          ...request,
          title: newValue || "",
        };
      });
    },
    [setNewRequest],
  );

  const onChangeBusinessJustification = useCallback(
    (
      event: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>,
      newValue?: string,
    ) => {
      setNewRequest((request) => {
        return {
          ...request,
          businessJustification: newValue || "",
        };
      });
    },
    [setNewRequest],
  );

  useEffect(
    () =>
      setRequestValid(
        newRequest.title?.length > 0 &&
          newRequest.businessJustification?.length > 0,
      ),
    [newRequest, setRequestValid],
  );

  // Submit Airlock request to API
  const create = useCallback(async () => {
    if (requestValid) {
      setCreating(true);
      setCreateError(false);
      try {
        const response = await apiCall(
          `${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.AirlockRequests}`,
          HttpMethod.Post,
          workspaceCtx.workspaceApplicationIdURI,
          newRequest,
        );
        props.onCreateRequest(response.airlockRequest);
        setHideCreateDialog(true);
      } catch (err: any) {
        err.userMessage = "Error submitting airlock request";
        setApiSubmitError(err);
        setCreateError(true);
      }
      setCreating(false);
    }
  }, [apiCall, newRequest, props, workspaceCtx, requestValid]);

  const dismissPanel = useCallback(() => navigate("../"), [navigate]);

  const renderFooter = useCallback(() => {
    let footer = <></>;
    if (newRequest.type) {
      footer = (
        <>
          <div style={{ textAlign: "end" }}>
            <DefaultButton
              onClick={() => setNewRequest({} as NewAirlockRequest)}
              styles={{ root: { marginRight: 8 } }}
            >
              Back
            </DefaultButton>
            <PrimaryButton
              onClick={() => setHideCreateDialog(false)}
              disabled={!requestValid}
            >
              Create
            </PrimaryButton>
          </div>
        </>
      );
    }
    return footer;
  }, [newRequest, setNewRequest, setHideCreateDialog, requestValid]);

  let title: string;
  let currentStep = <></>;

  // Render current step depending on whether type has been selected
  if (!newRequest.type) {
    title = "New airlock request";
    currentStep = (
      <Stack style={{ marginTop: "40px" }} tokens={stackTokens}>
        <DocumentCard
          aria-label="Import"
          type={DocumentCardType.compact}
          onClick={() =>
            setNewRequest({
              type: AirlockRequestType.Import,
            } as NewAirlockRequest)
          }
        >
          <DocumentCardPreview {...importPreviewGraphic} />
          <DocumentCardDetails>
            <DocumentCardTitle title="Import" styles={cardTitleStyles} />
            <DocumentCardTitle
              title="Import files into a workspace from outside of the TRE."
              shouldTruncate
              showAsSecondaryTitle
            />
          </DocumentCardDetails>
        </DocumentCard>

        <DocumentCard
          aria-label="Export"
          type={DocumentCardType.compact}
          onClick={() =>
            setNewRequest({
              type: AirlockRequestType.Export,
            } as NewAirlockRequest)
          }
        >
          <DocumentCardPreview {...exportPreviewGraphic} />
          <DocumentCardDetails>
            <DocumentCardTitle title="Export" styles={cardTitleStyles} />
            <DocumentCardTitle
              title="Export files from a workspace to the outside world."
              shouldTruncate
              showAsSecondaryTitle
            />
          </DocumentCardDetails>
        </DocumentCard>
      </Stack>
    );
  } else {
    title = `New airlock ${newRequest.type} request`;
    currentStep = (
      <Stack style={{ marginTop: "40px" }} tokens={stackTokens}>
        <TextField
          label="Title"
          placeholder="Enter a request title."
          value={newRequest.title}
          onChange={onChangetitle}
          rows={1}
          required
        />
        <TextField
          label="Business Justification"
          placeholder="Enter a justification for your request."
          value={newRequest.businessJustification}
          onChange={onChangeBusinessJustification}
          multiline
          rows={10}
          required
        />
      </Stack>
    );
  }

  return (
    <Panel
      headerText={title}
      isOpen={true}
      isLightDismiss={true}
      onDismiss={dismissPanel}
      onRenderFooterContent={renderFooter}
      isFooterAtBottom={true}
      closeButtonAriaLabel="Close"
      type={PanelType.custom}
      customWidth="450px"
    >
      <h4 style={{ fontWeight: "400", marginTop: 5 }}>
        <Icon
          iconName="CubeShape"
          style={{
            marginRight: "8px",
            fontSize: "22px",
            verticalAlign: "bottom",
          }}
        />
        {workspaceCtx.workspace?.properties?.display_name}
      </h4>
      {currentStep}
      <Dialog
        hidden={hideCreateDialog}
        onDismiss={() => setHideCreateDialog(true)}
        dialogContentProps={{
          title: "Create request?",
          subText: "Are you sure you want to create this request?",
        }}
      >
        {createError && <ExceptionLayout e={apiCreateError} />}
        {creating ? (
          <Spinner
            label="Creating..."
            ariaLive="assertive"
            labelPosition="top"
            size={SpinnerSize.large}
          />
        ) : (
          <DialogFooter>
            <PrimaryButton onClick={create} text="Create" />
            <DefaultButton
              onClick={() => setHideCreateDialog(true)}
              text="Cancel"
            />
          </DialogFooter>
        )}
      </Dialog>
    </Panel>
  );
};

const stackTokens: IStackTokens = { childrenGap: 20 };
const { palette, fonts } = getTheme();

const importPreviewGraphic: IDocumentCardPreviewProps = {
  previewImages: [
    {
      previewIconProps: {
        iconName: "ReleaseGate",
        styles: {
          root: {
            fontSize: fonts.superLarge.fontSize,
            color: "#0078d7",
            backgroundColor: palette.neutralLighterAlt,
          },
        },
      },
      width: 144,
    },
  ],
  styles: {
    previewIcon: { backgroundColor: palette.neutralLighterAlt },
  },
};

const exportPreviewGraphic: IDocumentCardPreviewProps = {
  previewImages: [
    {
      previewIconProps: {
        iconName: "Leave",
        styles: {
          root: {
            fontSize: fonts.superLarge.fontSize,
            color: "#0078d7",
            backgroundColor: palette.neutralLighterAlt,
          },
        },
      },
      width: 144,
    },
  ],
  styles: {
    previewIcon: { backgroundColor: palette.neutralLighterAlt },
  },
};

const cardTitleStyles = { root: { fontWeight: "600", paddingTop: 15 } };

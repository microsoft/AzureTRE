import {
  Dialog,
  PrimaryButton,
  DialogType,
  Stack,
  TooltipHost,
  TextField,
} from "@fluentui/react";
import React, { useState } from "react";
import { Resource } from "../../models/resource";

interface ConfirmCopyUrlToClipboardProps {
  resource: Resource;
  onDismiss: () => void;
}

// show a explanation about why connect is disabled, and show a copy to clipboard tool tip
export const ConfirmCopyUrlToClipboard: React.FunctionComponent<
  ConfirmCopyUrlToClipboardProps
> = (props: ConfirmCopyUrlToClipboardProps) => {
  const COPY_TOOL_TIP_DEFAULT_MESSAGE = "Copy to clipboard";

  const [copyToolTipMessage, setCopyToolTipMessage] = useState<string>(
    COPY_TOOL_TIP_DEFAULT_MESSAGE,
  );

  const copyUrlToClipboardProps = {
    type: DialogType.normal,
    title: "Access a Protected Endpoint",
    closeButtonAriaLabel: "Close",
    subText: `Copy the link below, paste it and use it from a workspace virtual machine`,
  };

  const dialogStyles = { main: { maxWidth: 450 } };
  const modalProps = {
    titleAriaId: "labelId",
    subtitleAriaId: "subTextId",
    isBlocking: true,
    styles: dialogStyles,
  };

  const handleCopyUrl = () => {
    navigator.clipboard.writeText(props.resource.properties.connection_uri);
    setCopyToolTipMessage("Copied");
    setTimeout(
      () => setCopyToolTipMessage(COPY_TOOL_TIP_DEFAULT_MESSAGE),
      3000,
    );
  };

  return (
    <>
      <Dialog
        hidden={false}
        onDismiss={() => props.onDismiss()}
        dialogContentProps={copyUrlToClipboardProps}
        modalProps={modalProps}
      >
        <Stack
          horizontal
          styles={{ root: { alignItems: "center", paddingTop: "7px" } }}
        >
          <Stack.Item grow>
            <TextField
              readOnly
              value={props.resource.properties.connection_uri}
            />
          </Stack.Item>
          <TooltipHost content={copyToolTipMessage}>
            <PrimaryButton
              iconProps={{ iconName: "copy" }}
              styles={{ root: { minWidth: "40px" } }}
              onClick={() => {
                handleCopyUrl();
              }}
            />
          </TooltipHost>
        </Stack>
      </Dialog>
    </>
  );
};

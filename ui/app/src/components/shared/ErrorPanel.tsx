import { Panel, PanelType } from "@fluentui/react";
import React from "react";
import stripAnsi from "strip-ansi";

interface ErrorPanelProps {
  errorMessage: string;
  isOpen: boolean;
  onDismiss: () => void;
}

export const ErrorPanel: React.FunctionComponent<ErrorPanelProps> = ({
  errorMessage,
  isOpen,
  onDismiss,
}) => {
  const cleanupError = (error: string) => {
    let cleanedError = stripAnsi(error);
    cleanedError = cleanedError.replace(/[│╷╵]/g, "\n");
    return cleanedError.trim();
  };

  return (
    <Panel
      headerText="Error Details"
      isOpen={isOpen}
      type={PanelType.large}
      closeButtonAriaLabel="Close"
      isLightDismiss
      onDismiss={onDismiss}
    >
      <div
        style={{
          width: "100%",
          whiteSpace: "pre-wrap",
          fontFamily: "monospace",
          backgroundColor: "#000",
          color: "#fff",
          padding: "10px",
        }}
      >
        {cleanupError(errorMessage)}
      </div>
    </Panel>
  );
};

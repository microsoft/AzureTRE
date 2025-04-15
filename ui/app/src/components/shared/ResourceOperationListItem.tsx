import { DefaultPalette, IStackItemStyles, Stack, Panel, PanelType, Link } from "@fluentui/react";
import React from "react";
import stripAnsi from 'strip-ansi';
interface ResourceOperationListItemProps {
  header: string;
  val: string;
}

export const ResourceOperationListItem: React.FunctionComponent<
  ResourceOperationListItemProps
> = (props: ResourceOperationListItemProps) => {
  const stackItemStyles: IStackItemStyles = {
    root: {
      padding: "5px 0",
      color: DefaultPalette.neutralSecondary,
    },
  };
  const [isOpen, setIsOpen] = React.useState(false);
  const cleanupError = (error: string) => {
    // Remove ANSI escape codes
    let cleanedError = stripAnsi(error);

    //Replace various vertical bars with new lines
    cleanedError = cleanedError.replace(/[│╷╵]/g, "\n");

    // Remove leading and trailing whitespace
    return cleanedError.trim();
  };

  // Check if the value is an error message
  const isError = props.val.includes("Error:") || props.val.includes("error:");

  return (
    <>
      <Stack wrap horizontal>
        <Stack.Item styles={stackItemStyles} style={{ width: "20%" }}>
          {props.header}
        </Stack.Item>

        {isError ? (
          <>
            <Stack.Item styles={stackItemStyles} style={{ width: "80%" }}>
              <Link onClick={() => setIsOpen(true)}>An error occurred, click to view the error details</Link>
            </Stack.Item>
            <Panel
              headerText="Error Details"
              isOpen={isOpen}
              type={PanelType.large}
              closeButtonAriaLabel="Close"
              isLightDismiss
              onDismiss={() => setIsOpen(false)}
            >
              <div style={{ width: "100%", whiteSpace: "pre-wrap", fontFamily: "monospace", backgroundColor: "#000", color: "#fff", padding: "10px" }}>
                {cleanupError(props.val)}
              </div>
            </Panel>
          </>
        ) : (
          <Stack.Item styles={stackItemStyles} style={{ width: "80%" }}>
            {props.val}
          </Stack.Item>
        )}
      </Stack>
    </>
  );
};

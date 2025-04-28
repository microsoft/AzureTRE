import { DefaultPalette, IStackItemStyles, Stack, Link } from "@fluentui/react";
import React from "react";
import { ErrorPanel } from "./ErrorPanel";

interface ResourceHistoryListItemProps {
  header: string;
  val: string;
}

export const ResourceHistoryListItem: React.FunctionComponent<
  ResourceHistoryListItemProps
> = (props: ResourceHistoryListItemProps) => {
  const stackItemStyles: IStackItemStyles = {
    root: {
      padding: "5px 0",
      color: DefaultPalette.neutralSecondary,
    },
  };
  const [isErrorPanelOpen, setIsErrorPanelOpen] = React.useState(false);
  const isError = typeof props.val === "string" && (props.val.toLowerCase().includes("error:") || props.val.toLowerCase().includes("error message:"));

  return (
    <>
      <Stack wrap horizontal>
        <Stack.Item styles={stackItemStyles} style={{ width: "20%" }}>
          {props.header}
        </Stack.Item>
        {isError ? (
          <>
            <Stack.Item styles={stackItemStyles} style={{ width: "80%" }}>
              <Link onClick={() => setIsErrorPanelOpen(true)}>An error occurred; click to view the error details</Link>
            </Stack.Item>
            <ErrorPanel
              errorMessage={props.val as string}
              isOpen={isErrorPanelOpen}
              onDismiss={() => setIsErrorPanelOpen(false)}
            />
          </>
        ) : (
          <Stack.Item styles={stackItemStyles} style={{ width: "80%" }}>
            : {props.val}
          </Stack.Item>
        )}
      </Stack>
    </>
  );
};

import { DefaultPalette, IStackItemStyles, Stack, Link } from "@fluentui/react";
import React from "react";
import { ErrorPanel } from "./ErrorPanel";

interface ResourceOperationListItemProps {
  header: string;
  val: string;
  isError?: boolean;
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
  const [isErrorPanelOpen, setIsErrorPanelOpen] = React.useState(false);

  return (
    <>
      <Stack wrap horizontal>
        <Stack.Item styles={stackItemStyles} style={{ width: "20%" }}>
          {props.header}
        </Stack.Item>

        {props.isError ? (
          <>
            <Stack.Item styles={stackItemStyles} style={{ width: "80%" }}>
              <Link onClick={() => setIsErrorPanelOpen(true)}>An error occurred; click to view the error details</Link>
            </Stack.Item>
            <ErrorPanel
              errorMessage={props.val}
              isOpen={isErrorPanelOpen}
              onDismiss={() => setIsErrorPanelOpen(false)}
            />
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

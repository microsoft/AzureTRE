import React from "react";
import { DefaultPalette, IStackItemStyles, Stack, Link } from "@fluentui/react";
import { OperationStep } from "../../models/operation";
import { ErrorPanel } from "./ErrorPanel";

interface ResourceOperationStepsListProps {
  header: String;
  val?: OperationStep[];
}

export const ResourceOperationStepsList: React.FunctionComponent<
  ResourceOperationStepsListProps
> = (props: ResourceOperationStepsListProps) => {
  const stackItemStyles: IStackItemStyles = {
    root: {
      padding: "5px 0",
      color: DefaultPalette.neutralSecondary,
    },
  };

  return (
    <Stack wrap horizontal>
      <Stack.Item styles={stackItemStyles} style={{ width: "20%" }}>
        {props.header}
      </Stack.Item>
      <div style={{ width: "80%" }}>
        {props.val?.map((step: OperationStep, i: number) => {
          const [isErrorPanelOpen, setIsErrorPanelOpen] = React.useState(false);
          const isError =
            typeof step.message === "string" &&
            (step.message.includes("Error:") || step.message.includes("error:"));

          return (
            <Stack.Item styles={stackItemStyles} key={i}>
              <div>
                {i + 1}
                {")"} {step.stepTitle}
              </div>
              {isError ? (
                <>
                  <Link onClick={() => setIsErrorPanelOpen(true)}>
                    An error occurred, click to view the error details
                  </Link>
                  <ErrorPanel
                    errorMessage={step.message}
                    isOpen={isErrorPanelOpen}
                    onDismiss={() => setIsErrorPanelOpen(false)}
                  />
                </>
              ) : (
                <div style={{ color: DefaultPalette.neutralTertiary }}>
                  {step.message}
                </div>
              )}
            </Stack.Item>
          );
        })}
      </div>
    </Stack>
  );
};

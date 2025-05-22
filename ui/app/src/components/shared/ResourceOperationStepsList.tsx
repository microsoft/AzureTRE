import React from "react";
import { DefaultPalette, IStackItemStyles, Stack, Link } from "@fluentui/react";
import { OperationStep, failedStates } from "../../models/operation";
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

  const [openErrorPanelIndex, setOpenErrorPanelIndex] = React.useState<number | null>(null);
  return (
    <Stack wrap horizontal>
      <Stack.Item styles={stackItemStyles} style={{ width: "20%" }}>
        {props.header}
      </Stack.Item>
      <div style={{ width: "80%" }}>
        {props.val?.map((step: OperationStep, i: number) => {
          const isError = step.status && failedStates.includes(step.status);
          return (
            <Stack.Item styles={stackItemStyles} key={i}>
              <div>
                {i + 1}
                {")"} {step.stepTitle}
              </div>
              {isError ? (
                <>
                  <Link onClick={() => setOpenErrorPanelIndex(i)}>
                    An error occurred; click to view the error details
                  </Link>
                  {openErrorPanelIndex === i && (
                    <ErrorPanel
                      errorMessage={step.message}
                      isOpen={openErrorPanelIndex === i}
                      onDismiss={() => setOpenErrorPanelIndex(null)}
                    />
                  )}
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

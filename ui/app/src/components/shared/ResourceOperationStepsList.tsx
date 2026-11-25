import React from "react";
import { getTheme, Link, Stack, Text } from "@fluentui/react";
import { OperationStep, failedStates } from "../../models/operation";
import { ErrorPanel } from "./ErrorPanel";
import { statusLabel, StatusIcon } from "./ResourceDetailsLayout";

interface ResourceOperationStepsListProps {
  steps?: OperationStep[];
}

const theme = getTheme();

export const ResourceOperationStepsList: React.FunctionComponent<ResourceOperationStepsListProps> = (props) => {
  const [openErrorPanelIndex, setOpenErrorPanelIndex] = React.useState<number | null>(null);

  return (
    <Stack as="ol" tokens={{ childrenGap: 8 }} styles={{ root: { listStyle: "none", padding: 0, margin: 0 } }}>
      {props.steps?.map((step: OperationStep, i: number) => {
        const isError = step.status && failedStates.includes(step.status);
        return (
          <Stack as="li" key={i} horizontal tokens={{ childrenGap: 10 }}>
            <div
              style={{ paddingTop: 2 }}
              role="img"
              aria-label={`Status: ${statusLabel(step.status)}`}
              title={statusLabel(step.status)}
            >
              <StatusIcon status={step.status} />
            </div>
            <Stack styles={{ root: { minWidth: 0 } }}>
              <Text>
                {i + 1}. {step.stepTitle}
              </Text>
              {isError ? (
                <>
                  <Link onClick={() => setOpenErrorPanelIndex(i)}>View error details</Link>
                  {openErrorPanelIndex === i && (
                    <ErrorPanel
                      errorMessage={step.message}
                      isOpen={openErrorPanelIndex === i}
                      onDismiss={() => setOpenErrorPanelIndex(null)}
                    />
                  )}
                </>
              ) : (
                step.message && (
                  <Text variant="small" style={{ color: theme.palette.neutralSecondary, wordBreak: "break-word" }}>
                    {step.message}
                  </Text>
                )
              )}
            </Stack>
          </Stack>
        );
      })}
    </Stack>
  );
};

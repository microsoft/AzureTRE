import { DefaultPalette, IStackItemStyles, Stack } from "@fluentui/react";
import { OperationStep } from "../../models/operation";

interface ResourceOperationStepsListProps {
  header: String,
  val?: OperationStep[]
}

export const ResourceOperationStepsList: React.FunctionComponent<ResourceOperationStepsListProps> = (props: ResourceOperationStepsListProps) => {

  const stackItemStyles: IStackItemStyles = {
    root: {
      padding: '5px 0',
      color: DefaultPalette.neutralSecondary
    }
  }

  return (
    <Stack wrap horizontal>
      <Stack.Item styles={stackItemStyles} style={{ width: '20%' }}>
        {props.header}
      </Stack.Item>
      <div style={{ width: '80%' }}>
        {props.val?.map((step: OperationStep, i: number) => {
          return (
            <Stack.Item styles={stackItemStyles} key={i}>
              <div >
                {step.stepTitle}
              </div>
              <div style={{ color: DefaultPalette.neutralTertiary }}>
                {step.message}
              </div>
            </Stack.Item>
          )
        })}
      </div>
    </Stack>
  );
}

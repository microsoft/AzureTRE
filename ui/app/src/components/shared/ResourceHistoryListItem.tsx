import { DefaultPalette, IStackItemStyles, Stack } from "@fluentui/react";

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
  return (
    <>
      <Stack wrap horizontal>
        <Stack.Item styles={stackItemStyles} style={{ width: "20%" }}>
          {props.header}
        </Stack.Item>
        <Stack.Item styles={stackItemStyles} style={{ width: "80%" }}>
          : {props.val}
        </Stack.Item>
      </Stack>
    </>
  );
};

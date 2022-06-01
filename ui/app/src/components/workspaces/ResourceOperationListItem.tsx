import { DefaultPalette, IStackItemStyles, Stack } from "@fluentui/react";

interface ResourceOperationListItemProps {
    header: String,
    val: String
}

export const ResourceOperationListItem: React.FunctionComponent<ResourceOperationListItemProps> = (props: ResourceOperationListItemProps) => {

    const stackItemStyles: IStackItemStyles = {
        root: {
            padding: 5,
            width: 150,
            color: DefaultPalette.neutralSecondary
        }
    }
    return(
        <>
            <Stack wrap horizontal>
                <Stack.Item grow styles={stackItemStyles}>
                    {props.header}
                </Stack.Item>
                <Stack.Item grow styles={stackItemStyles}>
                    : {props.val}
                </Stack.Item>
            </Stack>
        </>
    );
}
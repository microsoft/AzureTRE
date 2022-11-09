import { Stack, FontWeights, Text, Spinner, FontIcon, mergeStyles, getTheme, SpinnerSize, TooltipHost, ITooltipProps } from '@fluentui/react';
import React from 'react';
import { awaitingStates, failedStates, inProgressStates } from '../../models/operation';
import { Resource } from '../../models/resource';

interface StatusBadgeProps {
  status: string
  resource?: Resource
}

export const StatusBadge: React.FunctionComponent<StatusBadgeProps> = (props: StatusBadgeProps) => {
  let badgeType;
  if (props.status && inProgressStates.indexOf(props.status) !== -1) {
    badgeType = "inProgress";
  } else if (props.status && failedStates.indexOf(props.status) !== -1) {
    badgeType = "failed";
  } else if (!props.resource?.isEnabled) {
    badgeType = "disabled";
  }

  const failedTooltipProps: ITooltipProps = {
    onRenderContent: () => (
      <div style={{padding: '20px 24px'}}>
        <Text block variant="xLarge" style={{marginBottom: 12, fontWeight: FontWeights.semilight}}>
          {props.status.replace("_", " ")}
        </Text>
        <Text block variant="small">
          <Stack>
            <Stack.Item>
              <Stack horizontal tokens={{childrenGap: 5}}>
                <Stack.Item>
                  There was an issue with the latest deployment or update for this resource.
                  Please see the Operations panel within the resource for details.
                </Stack.Item>
              </Stack>
            </Stack.Item>
          </Stack>
        </Text>
      </div>
    ),
  };

  switch (badgeType) {
    case "inProgress":
      let label = awaitingStates.includes(props.status) ? 'pending' : props.status.replace("_", " ");
      return <Spinner label={label} style={{padding: 8}} ariaLive="assertive" labelPosition="right" size={SpinnerSize.xSmall} />
    case "failed":
      return (
        <TooltipHost id={`item-${props.resource?.id}-failed`} tooltipProps={failedTooltipProps}>
          <FontIcon
            aria-describedby={`item-${props.resource?.id}-failed`}
            aria-label="Error"
            iconName="AlertSolid"
            className={errorIcon}
          />
        </TooltipHost>
      );
    case "disabled":
      return (
        <>
          <TooltipHost
            content="This resource is disabled"
            id={`item-${props.resource?.id}-disabled`}
          >
            <FontIcon
              aria-label="Disabled"
              aria-describedby={`item-${props.resource?.id}-disabled`}
              iconName="Blocked2Solid"
              className={disabledIcon}
            />
          </TooltipHost>
        </>
      )
    default:
      return <></>
  }
};

const { palette } = getTheme();
const errorIcon = mergeStyles({
  color: palette.red,
  fontSize: 18,
  margin: 8
});
const disabledIcon = mergeStyles({
  color: palette.blackTranslucent40,
  fontSize: 18,
  margin: 8
});

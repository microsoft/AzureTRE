import { Callout, Stack, mergeStyleSets, FontWeights, Text, Icon, Spinner, FontIcon, mergeStyles, getTheme, SpinnerSize } from '@fluentui/react';
import React, { useState } from 'react';
import { awaitingStates, failedStates, inProgressStates, successStates } from '../../models/operation';

interface StatusBadgeProps {
  status: string
  resourceId?: string
}

export const StatusBadge: React.FunctionComponent<StatusBadgeProps> = (props: StatusBadgeProps) => {
  const [showInfo, setShowInfo] = useState(false);

  let badgeType;
  if (props.status && successStates.indexOf(props.status) !== -1) {
    badgeType = "success";
  } else if (props.status && inProgressStates.indexOf(props.status) !== -1) {
    badgeType = "inProgress";
  } else if (props.status && failedStates.indexOf(props.status) !== -1) {
    badgeType = "failed";
  }

  switch (badgeType) {
    case "inProgress":
      let label = awaitingStates.includes(props.status) ? 'pending' : props.status.replace("_", " ");
      return (
        <Spinner label={label} style={{padding: 8}} ariaLive="assertive" labelPosition="right" size={SpinnerSize.xSmall} />
      );
    case "failed":
      return (
        <>
          <span id={`item-${props.resourceId}`} style={{cursor: 'pointer', padding: 8}} onClick={(e) => {e.stopPropagation(); setShowInfo(true)}}>
            <FontIcon aria-label="Error" iconName="AlertSolid" className={errorIcon} />
          </span>
          {
            showInfo && <Callout
              className={styles.callout}
              ariaLabelledBy={`item-${props.resourceId}-label`}
              ariaDescribedBy={`item-${props.resourceId}-description`}
              role="dialog"
              gapSpace={0}
              target={`#item-${props.resourceId}`}
              onDismiss={() => setShowInfo(false)}
              setInitialFocus
            >
              <Text block variant="xLarge" className={styles.title} id={`item-${props.resourceId}-label`}>
                {props.status.replace("_", " ")}
              </Text>
              <Text block variant="small" id={`item-${props.resourceId}-description`}>
                <Stack>
                  <Stack.Item>
                    <Stack horizontal tokens={{childrenGap: 5}}>
                      <Stack.Item style={calloutValueStyles}>There was an issue with the latest deployment or update for this resource. Please see the Operations panel within the resource for details.</Stack.Item>
                    </Stack>
                  </Stack.Item>
                </Stack>
              </Text>
            </Callout>
          }
        </>
      );
    default:
      return <></>
  }
};

const calloutValueStyles: React.CSSProperties = {
  width: 'auto'
}

const { palette } = getTheme();
const errorIcon = mergeStyles({
  color: palette.red,
  fontSize: 18
});


const styles = mergeStyleSets({
  button: {
    width: 130,
  },
  callout: {
    width: 350,
    padding: '20px 24px',
  },
  title: {
    marginBottom: 12,
    fontWeight: FontWeights.semilight
  },
  link: {
    display: 'block',
    marginTop: 20,
  }
});

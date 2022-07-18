import { Callout, Stack, mergeStyleSets, FontWeights, Text, Icon } from '@fluentui/react';
import React, { useState } from 'react';
import { failedStates, inProgressStates, successStates } from '../../models/operation';

interface StatusBadgeProps {
  status: string
  resourceId?: string
}

export const StatusBadge: React.FunctionComponent<StatusBadgeProps> = (props: StatusBadgeProps) => {
  const [showInfo, setShowInfo] = useState(false);

  let baseClass = "tre-badge";
  let badgeType = "";
  if (props.status && successStates.indexOf(props.status) !== -1) { badgeType = "success"; }
  else if (props.status && inProgressStates.indexOf(props.status) !== -1) { badgeType = "inProgress"; baseClass += " tre-badge-in-progress"; }
  else if (props.status && failedStates.indexOf(props.status) !== -1) { badgeType = "failed"; baseClass += " tre-badge-failed"; }

  switch (badgeType) {
    case "inProgress":
      return (<span className={`${baseClass} tre-badge-in-progress`}>{props.status.replace("_", " ")}</span>);
    case "failed":
      return (
        <>
          <span id={`item-${props.resourceId}`} style={{cursor: 'pointer'}} onClick={() => setShowInfo(true)} className={`${baseClass} tre-badge tre-badge-failed`}>
            <Icon iconName="Error" />
          </span>
          {
            showInfo &&
            <Callout
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
                {props.status}
              </Text>
              <Text block variant="small" id={`item-${props.resourceId}-description`}>
                <Stack>
                  <Stack.Item>
                    <Stack horizontal tokens={{ childrenGap: 5 }}>
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

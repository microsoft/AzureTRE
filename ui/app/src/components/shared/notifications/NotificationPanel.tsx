import { Callout, DirectionalHint, FontWeights, Icon, Link, mergeStyleSets, MessageBar, MessageBarType, Panel, ProgressIndicator, Text } from '@fluentui/react';
import React, { useEffect, useState } from 'react';
import { completedStates, inProgressStates, Operation, successStates } from '../../../models/operation';
import { NotificationItem } from './NotificationItem';
import { IconButton } from '@fluentui/react/lib/Button';
import { HttpMethod, useAuthApiCall } from '../../../hooks/useAuthApiCall';
import { ApiEndpoint } from '../../../models/apiEndpoints';
import { Resource } from '../../../models/resource';
import { useAppDispatch, useAppSelector } from '../../../hooks/customReduxHooks';
import { setInitialOperations, dismissCompleted } from '../../shared/notifications/operationsSlice';

export const NotificationPanel: React.FunctionComponent = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [showCallout, setShowCallout] = useState(false);
  const [calloutDetails, setCalloutDetails] = useState({ title: '', text: '', success: true });
  const apiCall = useAuthApiCall();
  const operations = useAppSelector((state) => state.operations);
  const dispatch = useAppDispatch();

  useEffect(() => {
    const loadAllOps = async () => {
      let opsToAdd = (await apiCall(`${ApiEndpoint.Operations}`, HttpMethod.Get)).operations as Array<Operation>;
      dispatch(setInitialOperations(opsToAdd));
    };

    loadAllOps();
  }, [apiCall, dispatch])

  const callout = (o: Operation, r: Resource) => {
    if (successStates.includes(o.status)) {
      setCalloutDetails({
        title: "Operation Succeeded",
        text: `${o.action} for ${r.properties.display_name} completed successfully`,
        success: true
      });
    } else {
      setCalloutDetails({
        title: "Operation Failed",
        text: `${o.action} for ${r.properties.display_name} completed with status ${o.status}`,
        success: false
      });
    }

    setShowCallout(true);
  }

  return (
    <>
      <IconButton id="tre-notification-btn" className='tre-notifications-button' iconProps={{ iconName: 'Ringer' }} onClick={() => setIsOpen(true)} title="Notifications" ariaLabel="Notifications" />

      {
        operations.items && operations.items.filter((o: Operation) => inProgressStates.includes(o.status)).length > 0 &&
        <span style={{ marginTop: -15, display: 'block' }}>
          <ProgressIndicator barHeight={2} />
        </span>
      }

      {
        showCallout && !isOpen &&
        <Callout
          ariaLabelledBy={'labelId'}
          ariaDescribedBy={'descriptionId'}
          role="dialog"
          className={styles.callout}
          gapSpace={0}
          target={'#tre-notification-btn'}
          isBeakVisible={true}
          beakWidth={20}
          onDismiss={() => { setShowCallout(false) }}
          directionalHint={DirectionalHint.bottomLeftEdge}
          setInitialFocus
        >
          <Text block variant="xLarge" id={'labelId'}>
            {calloutDetails.success ?
              <Icon iconName="CheckMark" style={{ color: '#009900', position: 'relative', top: 4, marginRight: 10 }} />
              :
              <Icon iconName="Error" style={{ color: '#990000', position: 'relative', top: 4, marginRight: 10 }} />
            }
            {calloutDetails.title}
          </Text>
          <br />
          <Text block variant="medium" id={'descriptionId'}>
            {calloutDetails.text}
          </Text>
        </Callout>
      }
      <Panel
        isLightDismiss
        isHiddenOnDismiss={true}
        headerText="Notifications"
        isOpen={isOpen}
        onDismiss={() => { setIsOpen(false) }}
        closeButtonAriaLabel="Close Notifications"
      >
        <div className="tre-notifications-dismiss">
          <Link href="#" onClick={(e) => { dispatch(dismissCompleted()); return false; }} disabled={
            operations.items.filter((o: Operation) => o.dismiss !== true && completedStates.includes(o.status)).length === 0
          }>Dismiss Completed</Link>
        </div>
        {
          operations.items.length === 0 &&
          <div style={{ marginTop: '20px' }}>
            <MessageBar
              messageBarType={MessageBarType.success}
              isMultiline={false}
            >
              No notifications to display
            </MessageBar>
          </div>
        }
        <ul className="tre-notifications-list">
          {
            operations.items.map((o: Operation, i: number) => {
              return (
                <NotificationItem operation={o} key={i} showCallout={(o: Operation, r: Resource) => callout(o, r)} />
              )
            })
          }
        </ul>
      </Panel>
    </>
  );
};

const styles = mergeStyleSets({
  buttonArea: {
    verticalAlign: 'top',
    display: 'inline-block',
    textAlign: 'center',
    margin: '0 100px',
    minWidth: 130,
    height: 32,
  },
  configArea: {
    width: 300,
    display: 'inline-block',
  },
  button: {
    width: 130,
  },
  callout: {
    width: 320,
    padding: '20px 24px',
  },
  title: {
    marginBottom: 12,
    fontWeight: FontWeights.semilight,
  },
  link: {
    display: 'block',
    marginTop: 20,
  },
});

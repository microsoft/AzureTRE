import { Callout, DirectionalHint, FontWeights, Link, mergeStyleSets, MessageBar, MessageBarType, Panel, Text } from '@fluentui/react';
import React, { useContext, useEffect, useRef, useState } from 'react';
import { completedStates, Operation } from '../../../models/operation';
import { OperationsContext } from '../../../contexts/OperationsContext';
import { NotificationItem } from './NotificationItem';
import { IconButton } from '@fluentui/react/lib/Button';
import { HttpMethod, useAuthApiCall } from '../../../hooks/useAuthApiCall';
import { ApiEndpoint } from '../../../models/apiEndpoints';

export const NotificationPanel: React.FunctionComponent = () => {
  const opsContext = useContext(OperationsContext);
  const [isOpen, setIsOpen] = useState(false);
  const [showCallout, setShowCallout] = useState(false);
  const apiCall = useAuthApiCall();

  useEffect(() => {
    const loadAllOps = async () => {
      let opsToAdd = (await apiCall(`${ApiEndpoint.Operations}/my`, HttpMethod.Get)).operations as Array<Operation>;
      opsContext.addOperations(opsToAdd);
    };

    loadAllOps();
  }, [apiCall])

  return (
    <>
      <IconButton id="tre-notification-btn" className='tre-notifications-button' iconProps={{ iconName: opsContext.operations.length > 0 ? 'RingerSolid' : 'Ringer' }} onClick={() => setIsOpen(true)} title="Notifications" ariaLabel="Notifications" />
      {
        showCallout &&
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
            Resource operation completed
          </Text>
          <br />
          <Text block variant="medium" id={'descriptionId'}>
            See notifications panel for detail
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
          <Link href="#" onClick={(e) => { opsContext.dismissCompleted(); return false; }} disabled={
            opsContext.operations.filter((o: Operation) => o.dismiss !== true && completedStates.includes(o.status)).length === 0
          }>Dismiss Completed</Link>
        </div>
        {
          opsContext.operations.length === 0 &&
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
            opsContext.operations.map((o: Operation, i: number) => {
              return (
                <NotificationItem operation={o} key={i} showCallout={() => setShowCallout(true)} />
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

import { Dialog, DialogFooter, PrimaryButton, DefaultButton, DialogType, Spinner } from '@fluentui/react';
import React, { useContext, useState } from 'react';
import { Resource } from '../../models/resource';
import { HttpMethod, ResultType, useAuthApiCall } from '../../hooks/useAuthApiCall';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import { OperationsContext } from '../../contexts/OperationsContext';
import { ResourceType } from '../../models/resourceType';

interface ConfirmDeleteProps {
  resource: Resource,
  onDismiss: () => void
}

// show a 'are you sure' modal, and then send a patch if the user confirms
export const ConfirmDeleteResource: React.FunctionComponent<ConfirmDeleteProps> = (props: ConfirmDeleteProps) => {
  const apiCall = useAuthApiCall();
  const [isSending, setIsSending] = useState(false);
  const workspaceCtx = useContext(WorkspaceContext);
  const opsCtx = useContext(OperationsContext);

  const deleteProps = {
    type: DialogType.normal,
    title: 'Delete Resource?',
    closeButtonAriaLabel: 'Close',
    subText: `Are you sure you want to permanently delete ${props.resource.properties.display_name}?`,
  };

  const dialogStyles = { main: { maxWidth: 450 } };
  const modalProps = {
    titleAriaId: 'labelId',
    subtitleAriaId: 'subTextId',
    isBlocking: true,
    styles: dialogStyles
  };

  const wsAuth = (props.resource.resourceType === ResourceType.WorkspaceService || props.resource.resourceType === ResourceType.UserResource);

  const deleteCall = async () => {
    setIsSending(true);
    let op = await apiCall(props.resource.resourcePath, HttpMethod.Delete, wsAuth ? workspaceCtx.workspaceApplicationIdURI : undefined, undefined, ResultType.JSON);
    opsCtx.addOperations([op.operation]);
    setIsSending(false);
    props.onDismiss();
  }

  return (<>
    <Dialog
      hidden={false}
      onDismiss={() => props.onDismiss()}
      dialogContentProps={deleteProps}
      modalProps={modalProps}
    >
      {!isSending ?
        <DialogFooter>
          <PrimaryButton text="Delete" onClick={() => deleteCall()} />
          <DefaultButton text="Cancel" onClick={() => props.onDismiss()} />

        </DialogFooter>
        :
        <Spinner label="Sending request..." ariaLive="assertive" labelPosition="right" />
      }
    </Dialog>
  </>);
};

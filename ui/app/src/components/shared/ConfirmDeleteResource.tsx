import { Dialog, DialogFooter, PrimaryButton, DefaultButton, DialogType, Spinner } from '@fluentui/react';
import React, { useContext, useState } from 'react';
import { Resource } from '../../models/resource';
import { HttpMethod, ResultType, useAuthApiCall } from '../../hooks/useAuthApiCall';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import { ResourceType } from '../../models/resourceType';
import { APIError } from '../../models/exceptions';
import { LoadingState } from '../../models/loadingState';
import { ExceptionLayout } from './ExceptionLayout';
import { useAppDispatch } from '../../hooks/customReduxHooks';
import { addUpdateOperation } from '../shared/notifications/operationsSlice';

interface ConfirmDeleteProps {
  resource: Resource,
  onDismiss: () => void
}

// show a 'are you sure' modal, and then send a patch if the user confirms
export const ConfirmDeleteResource: React.FunctionComponent<ConfirmDeleteProps> = (props: ConfirmDeleteProps) => {
  const apiCall = useAuthApiCall();
  const [apiError, setApiError] = useState({} as APIError);
  const [loading, setLoading] = useState(LoadingState.Ok);
  const workspaceCtx = useContext(WorkspaceContext);
  const dispatch = useAppDispatch();

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
    setLoading(LoadingState.Loading);
    try {
      let op = await apiCall(props.resource.resourcePath, HttpMethod.Delete, wsAuth ? workspaceCtx.workspaceApplicationIdURI : undefined, undefined, ResultType.JSON);
      dispatch(addUpdateOperation(op.operation));
      props.onDismiss();
    } catch (err: any) {
      err.userMessage = 'Failed to delete resource';
      setApiError(err);
      setLoading(LoadingState.Error);
    }
  }

  return (<>
    <Dialog
      hidden={false}
      onDismiss={() => props.onDismiss()}
      dialogContentProps={deleteProps}
      modalProps={modalProps}
    >
      {
        loading === LoadingState.Ok &&
        <DialogFooter>
          <PrimaryButton text="Delete" onClick={() => deleteCall()} />
          <DefaultButton text="Cancel" onClick={() => props.onDismiss()} />
        </DialogFooter>
      }
      {
        loading === LoadingState.Loading &&
        <Spinner label="Sending request..." ariaLive="assertive" labelPosition="right" />
      }
      {
        loading === LoadingState.Error &&
        <ExceptionLayout e={apiError} />
      }
    </Dialog>
  </>);
};

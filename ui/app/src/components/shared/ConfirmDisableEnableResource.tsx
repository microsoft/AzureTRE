import { Dialog, DialogFooter, PrimaryButton, DefaultButton, DialogType, Spinner } from '@fluentui/react';
import React, { useContext, useState } from 'react';
import { Resource } from '../../models/resource';
import { HttpMethod, ResultType, useAuthApiCall } from '../../hooks/useAuthApiCall';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import { ResourceType } from '../../models/resourceType';
import { LoadingState } from '../../models/loadingState';
import { APIError } from '../../models/exceptions';
import { ExceptionLayout } from './ExceptionLayout';
import { useAppDispatch } from '../../hooks/customReduxHooks';
import { addUpdateOperation } from '../shared/notifications/operationsSlice';

interface ConfirmDisableEnableResourceProps {
  resource: Resource,
  isEnabled: boolean,
  onDismiss: () => void
}

// show a 'are you sure' modal, and then send a patch if the user confirms
export const ConfirmDisableEnableResource: React.FunctionComponent<ConfirmDisableEnableResourceProps> = (props: ConfirmDisableEnableResourceProps) => {
  const apiCall = useAuthApiCall();
  const [loading, setLoading] = useState(LoadingState.Ok);
  const [apiError, setApiError] = useState({} as APIError);
  const workspaceCtx = useContext(WorkspaceContext);
  const dispatch = useAppDispatch();

  const disableProps = {
    type: DialogType.normal,
    title: 'Disable Resource?',
    closeButtonAriaLabel: 'Close',
    subText: `Are you sure you want to disable ${props.resource.properties.display_name}?`,
  };

  const enableProps = {
    type: DialogType.normal,
    title: 'Enable Resource?',
    closeButtonAriaLabel: 'Close',
    subText: `Are you sure you want to enable ${props.resource.properties.display_name}?`,
  };

  const dialogStyles = { main: { maxWidth: 450 } };
  const modalProps = {
    titleAriaId: 'labelId',
    subtitleAriaId: 'subTextId',
    isBlocking: true,
    styles: dialogStyles
  };

  const wsAuth = (props.resource.resourceType === ResourceType.WorkspaceService || props.resource.resourceType === ResourceType.UserResource);

  const toggleDisableCall = async () => {
    setLoading(LoadingState.Loading);
    try {
      let body = { isEnabled: props.isEnabled }
      let op = await apiCall(props.resource.resourcePath, HttpMethod.Patch, wsAuth ? workspaceCtx.workspaceApplicationIdURI : undefined, body, ResultType.JSON, undefined, undefined, props.resource._etag);
      dispatch(addUpdateOperation(op.operation));
      props.onDismiss();
    } catch (err: any) {
      err.userMessage = 'Failed to enable/disable resource';
      setApiError(err);
      setLoading(LoadingState.Error);
    }
  }

  return (
    <>
      <Dialog
        hidden={false}
        onDismiss={() => props.onDismiss()}
        dialogContentProps={props.isEnabled ? enableProps : disableProps}
        modalProps={modalProps}
      >
        {
          loading === LoadingState.Ok &&
          <DialogFooter>
            {props.isEnabled ?
              <PrimaryButton text="Enable" onClick={() => toggleDisableCall()} />
              :
              <PrimaryButton text="Disable" onClick={() => toggleDisableCall()} />
            }
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

import { Dialog, DialogFooter, PrimaryButton, DialogType, Spinner, Dropdown, MessageBar, MessageBarType, DropdownMenuItemType, IDropdownOption, Icon, Stack, Label, IconButton, IDropdownProps } from '@fluentui/react';
import React, { useContext, useState } from 'react';
import { AvailableUpgrade, Resource } from '../../models/resource';
import { HttpMethod, ResultType, useAuthApiCall } from '../../hooks/useAuthApiCall';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import { ResourceType } from '../../models/resourceType';
import { APIError } from '../../models/exceptions';
import { LoadingState } from '../../models/loadingState';
import { ExceptionLayout } from './ExceptionLayout';
import { useAppDispatch } from '../../hooks/customReduxHooks';
import { addUpdateOperation } from '../shared/notifications/operationsSlice';

interface ConfirmUpgradeProps {
  resource: Resource,
  onDismiss: () => void
}

export const ConfirmUpgradeResource: React.FunctionComponent<ConfirmUpgradeProps> = (props: ConfirmUpgradeProps) => {
  const apiCall = useAuthApiCall();
  const [selectedVersion, setSelectedVersion] = useState("")
  const [apiError, setApiError] = useState({} as APIError);
  const [loading, setLoading] = useState(LoadingState.Ok);
  const workspaceCtx = useContext(WorkspaceContext);
  const dispatch = useAppDispatch();

  const upgradeProps = {
    type: DialogType.normal,
    title: `Upgrade Template Version?`,
    closeButtonAriaLabel: 'Close',
    subText: `Are you sure you want upgrade the template version of ${props.resource.properties.display_name} from version ${props.resource.templateVersion}?`,
  };

  const dialogStyles = { main: { maxWidth: 450 } };
  const modalProps = {
    titleAriaId: 'labelId',
    subtitleAriaId: 'subTextId',
    isBlocking: true,
    styles: dialogStyles
  };

  const wsAuth = (props.resource.resourceType === ResourceType.WorkspaceService || props.resource.resourceType === ResourceType.UserResource);

  const upgradeCall = async () => {
    setLoading(LoadingState.Loading);
    try {
      let body = { templateVersion: selectedVersion }
      let op = await apiCall(props.resource.resourcePath, HttpMethod.Patch, wsAuth ? workspaceCtx.workspaceApplicationIdURI : undefined, body, ResultType.JSON, undefined, undefined, props.resource._etag);
      dispatch(addUpdateOperation(op.operation));
      props.onDismiss();
    } catch (err: any) {
      err.userMessage = 'Failed to upgrade resource';
      setApiError(err);
      setLoading(LoadingState.Error);
    }
  }

  const onRenderOption = (option: any): JSX.Element => {
    return (
      <div>
        {option.data && option.data.icon && (
          <Icon style={{ marginRight: '8px' }} iconName={option.data.icon} aria-hidden="true" title={option.data.icon} />
        )}
        <span>{option.text}</span>
      </div>
    );
  };

  const convertToDropDownOptions = (upgrade: Array<AvailableUpgrade>) => {
    return upgrade.map(upgrade => ({ "key": upgrade.version, "text": upgrade.version, data: { icon: upgrade.forceUpdateRequired ? 'Warning' : '' } }))
  }

  const getDropdownOptions = () => {
    const options = []
    const nonMajorUpgrades = props.resource.availableUpgrades.filter(upgrade => !upgrade.forceUpdateRequired)
    options.push(...convertToDropDownOptions(nonMajorUpgrades))
    return options;
  }

  return (<>
    <Dialog
      hidden={false}
      onDismiss={() => props.onDismiss()}
      dialogContentProps={upgradeProps}
      modalProps={modalProps}
    >
      {
        loading === LoadingState.Ok &&
        <>
          <MessageBar messageBarType={MessageBarType.warning} >Upgrading the template version is irreversible.</MessageBar>
          <DialogFooter>
            <Dropdown
              placeholder='Select Version'
              options={getDropdownOptions()}
              onRenderOption={onRenderOption}
              styles={{ dropdown: { width: 125 } }}
              onChange={(event, option) => { option && setSelectedVersion(option.text); }}
              selectedKey={selectedVersion}
            />
            <PrimaryButton primaryDisabled={!selectedVersion} text="Upgrade" onClick={() => upgradeCall()} />
          </DialogFooter>
        </>
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

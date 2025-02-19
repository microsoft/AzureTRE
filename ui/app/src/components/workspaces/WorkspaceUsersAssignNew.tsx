import * as React from 'react';
import { Dropdown, IDropdownOption, Label, Panel, PanelType, PrimaryButton, Spinner, Stack } from "@fluentui/react";
import { IPersonaProps } from '@fluentui/react/lib/Persona';
import {
  IBasePickerSuggestionsProps,
  NormalPeoplePicker
} from '@fluentui/react/lib/Pickers';
import { useCallback, useContext, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { HttpMethod, useAuthApiCall } from "../../hooks/useAuthApiCall";
import { ApiEndpoint } from "../../models/apiEndpoints";
import { APIError } from "../../models/exceptions";
import { ExceptionLayout } from "../shared/ExceptionLayout";

interface WorkspaceUsersAssignProps {
  onAssignUser: (request: any) => void;
}

interface AssignableUser {
  displayName: string;
  userPrincipalName: string;
  id: string;
}

interface WorkspaceRole {
  id: string;
  displayName: string;
}

const suggestionProps: IBasePickerSuggestionsProps = {
  suggestionsHeaderText: 'Suggested Users',
  noResultsFoundText: 'No results found',
  loadingText: 'Loading',
  showRemoveButtons: true,
  suggestionsAvailableAlertText: 'People Picker Suggestions available',
  suggestionsContainerAriaLabel: 'Suggested contacts',
};

export const WorkSpaceUsersAssignNew: React.FunctionComponent<WorkspaceUsersAssignProps> = (props: WorkspaceUsersAssignProps) => {
  const workspaceCtx = useContext(WorkspaceContext);
  const { workspace } = workspaceCtx;

  const navigate = useNavigate();
  const apiCall = useAuthApiCall();
  const picker = React.useRef(null);

  const onFilterChanged = async (filter: string): Promise<IPersonaProps[]> => {
    if (filter) {
      return filterPersonasByText(filter);
    } else {
      return [];
    }
  };

  const filterPersonasByText = async (filterText: string): Promise<IPersonaProps[]> => {
    try {
      const scopeId = "";
      const response = await apiCall(`${ApiEndpoint.Workspaces}/${workspace.id}/${ApiEndpoint.AssignableUsers}?filter=${filterText}`, HttpMethod.Get, scopeId);
      const assignableUsers = response.assignable_users;

      const options: IPersonaProps[] = assignableUsers.map((assignableUser: AssignableUser) => ({
        text: assignableUser.displayName,
        secondaryText: assignableUser.userPrincipalName,
        key: assignableUser.id
      }));

      return options;
    }
    catch (err: any) {
      err.userMessage = 'Error retrieving assignable users';
    }
    return [];
  };

  const onChange = (items?: IPersonaProps[] | undefined): void => {
    if (items && items.length > 0) {
      setSelectedUsers(items.map(item => item.key as string));
    }
    else {
      setSelectedUsers(null);
    }
  };

  const [roleOptions, setRoleOptions] = useState<IDropdownOption[]>([]);
  const [selectedUsers, setSelectedUsers] = useState<string[] | null>(null);
  const [selectedRole, setSelectedRole] = useState<string | null>(null);
  const [assigning, setAssigning] = useState(false);
  const [hasAssignmentError, setHasAssignmentError] = useState(false);
  const [assignmentError, setAssignmentError] = useState({} as APIError);

  const onRoleChange = (event: any, option: any) => {
    setSelectedRole(option ? option.key : null);
  };

  const dismissPanel = useCallback(() => navigate('../'), [navigate]);

  const getWorkspaceRoles = useCallback(async () => {
    try {
      const scopeId = "";
      const response = await apiCall(`${ApiEndpoint.Workspaces}/${workspace.id}/${ApiEndpoint.Roles}`, HttpMethod.Get, scopeId);

      const options: IDropdownOption[] = response.roles.map((workspaceRole: WorkspaceRole) => ({
        key: workspaceRole.id,
        text: workspaceRole.displayName
      }));

      setRoleOptions(options);
    }
    catch (err: any) {
      err.userMessage = 'Error retrieving assignable users';
    }

  }, [apiCall, workspace.id]);

  useEffect(() => {
    getWorkspaceRoles();
  }, [getWorkspaceRoles]);

  const assign = useCallback(async () => {
    setAssigning(true);

    const scopeId = "";
    try {
      const response = await apiCall(`${ApiEndpoint.Workspaces}/${workspace.id}/${ApiEndpoint.Users}/assign`, HttpMethod.Post, scopeId, {
        role_id: selectedRole,
        user_ids: selectedUsers
      });
      props.onAssignUser(response);
    }
    catch (err: any) {
      err.userMessage = 'Error assigning workspace user';
      setHasAssignmentError(true);
      setAssignmentError(err);
    }
    setAssigning(false);

  }, [selectedUsers, apiCall, workspace.id, selectedRole, props]);

  const renderFooter = useCallback(() => {
    let footer = <></>
    footer = <>
      <div style={{ textAlign: 'end' }}>
        <PrimaryButton onClick={() => assign()} disabled={assigning || (!selectedUsers || !selectedRole)}>Assign</PrimaryButton>
      </div>
    </>
    return footer;
  }, [selectedUsers, selectedRole, assign, assigning]);

  return (
    <Panel
      headerText="Assign users to a role"
      isOpen={true}
      isLightDismiss={true}
      onDismiss={dismissPanel}
      onRenderFooterContent={renderFooter}
      isFooterAtBottom={true}
      closeButtonAriaLabel="Close"
      type={PanelType.custom}
      customWidth="450px"
    >
      <Stack tokens={{ childrenGap: 20 }} styles={{ root: { paddingTop: 20 } }}>
        <Stack tokens={{ childrenGap: 10 }} verticalAlign="center">
          <Label>User</Label>
          <NormalPeoplePicker
            onResolveSuggestions={onFilterChanged}
            pickerSuggestionsProps={suggestionProps}
            className={'ms-PeoplePicker'}
            key={'normal'}
            selectionAriaLabel={'Selected user'}
            removeButtonAriaLabel={'Remove'}
            inputProps={{
              'aria-label': 'User Picker',
            }}
            componentRef={picker}
            resolveDelay={300}
            required={true}
            onChange={onChange}
          />
        </Stack>
        <Stack tokens={{ childrenGap: 10 }} verticalAlign="center">
          <Label>Role</Label>
          <Dropdown
            placeholder="Select a role"
            options={roleOptions}
            disabled={assigning}
            styles={{ root: { width: '100%' } }}
            onChange={onRoleChange}
          />
        </Stack>
        {
          assigning && <Stack>
            <Stack.Item style={{ paddingTop: '10px', paddingBottom: '10px' }}>
              <Spinner />
            </Stack.Item>
          </Stack>
        }
        {
          hasAssignmentError && <ExceptionLayout e={assignmentError} />
        }
      </Stack>
    </Panel>

  )
}


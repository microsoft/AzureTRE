import { ComboBox, Dropdown, IComboBoxOption, IDropdownOption, ISelectableOption, Label,  Panel, PanelType, PrimaryButton, Spinner, Stack } from "@fluentui/react";
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
  name: string;
  email: string;
}

interface WorkspaceRole {
  value: string;
  displayName: string;
}

export const WorkSpaceUsersAssignNew: React.FunctionComponent<WorkspaceUsersAssignProps> = (props: WorkspaceUsersAssignProps) => {
  const workspaceCtx = useContext(WorkspaceContext);
  const { workspace } = workspaceCtx;

  const navigate = useNavigate();
  const apiCall = useAuthApiCall();

  const [userOptions, setUserOptions] = useState<IComboBoxOption[]>([]);
  const [roleOptions, setRoleOptions] = useState<IDropdownOption[]>([]);

  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [selectedRole, setSelectedRole] = useState<string | null>(null);

  const [assigning, setAssigning] = useState(false);
  const [hasAssignmentError, setHasAssignmentError] = useState(false);
  const [assignmentError, setAssignmentError] = useState({} as APIError);

  const onUserChange = (event: any) => {
    setSelectedUser(event ? event.target.value : null);
  };

  const onRoleChange = (event: any, option: any) => {
    setSelectedRole(option ? option.key : null);
  };

  const dismissPanel = useCallback(() => navigate('../'), [navigate]);

  const getAssignableUsers = useCallback(async () => {
    try {
      const scopeId = "";
      const response = await apiCall(`${ApiEndpoint.Workspaces}/${workspace.id}/${ApiEndpoint.AssignableUsers}`, HttpMethod.Get, scopeId);
      const assignableUsers = response.assignable_users;

      const options: IComboBoxOption[] = assignableUsers.map((assignableUser: AssignableUser) => ({
        key: assignableUser.email,
        text: assignableUser.email,
        data: { name: assignableUser.name },
      }));

      setUserOptions(options);
    }
    catch (err: any) {
      err.userMessage = 'Error retrieving assignable users';
    }

  }, [apiCall, workspace.id]);

  const getWorkspaceRoles = useCallback(async () => {
    try {
      const scopeId = "";
      const response = await apiCall(`${ApiEndpoint.Workspaces}/${workspace.id}/${ApiEndpoint.Roles}`, HttpMethod.Get, scopeId);

      const options: IDropdownOption[] = response.roles.map((workspaceRole: WorkspaceRole) => ({
        key: workspaceRole.value,
        text: workspaceRole.displayName
      }));

      setRoleOptions(options);
    }
    catch (err: any) {
      err.userMessage = 'Error retrieving assignable users';
    }

  }, [apiCall, workspace.id]);

  useEffect(() => {
    getAssignableUsers();
    getWorkspaceRoles();
  }, [getAssignableUsers, getWorkspaceRoles]);

  const assign = useCallback(async () => {
    setAssigning(true);

    const encodedUser=selectedUser?.replaceAll('#', '%23');

    const scopeId = "";
    try {
      const response = await apiCall(`${ApiEndpoint.Workspaces}/${workspace.id}/${ApiEndpoint.Users}/assign?user_email=${encodedUser}&role_name=${selectedRole}`, HttpMethod.Post, scopeId);
      props.onAssignUser(response);
    }
    catch (err: any) {
      err.userMessage = 'Error assigning workspace user';
      setHasAssignmentError(true);
      setAssignmentError(err);
    }
    setAssigning(false);

  }, [selectedUser, apiCall, workspace.id, selectedRole, props]);

  const renderFooter = useCallback(() => {
    let footer = <></>
    footer = <>
      <div style={{ textAlign: 'end' }}>
        <PrimaryButton onClick={() => assign()} disabled={assigning || (!selectedUser || !selectedRole)}>Assign</PrimaryButton>
      </div>
    </>
    return footer;
  }, [selectedUser, selectedRole, assign, assigning]);

  const onRenderOption = (option?: ISelectableOption<any>): JSX.Element | null => {
    if (!option) {
      return null;
    }
    return (
      <div style={{ padding: '8px 0' }}>
        <div style={{ fontWeight: 'bold' }}>{option.data?.name}</div>
        <div>{option.text}</div>
      </div>
    );
  };

  return (
    <Panel
      headerText="Assign user to a role"
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
          <ComboBox
            placeholder="Enter a user's email address"
            options={userOptions}
            styles={{ root: { width: '100%' } }}
            disabled={assigning}
            onChange={onUserChange}
            onRenderOption={onRenderOption}
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

import * as React from 'react';
import { useState, useCallback, useEffect, useMemo, useContext } from 'react';
import { GroupedList, IGroup } from '@fluentui/react/lib/GroupedList';
import { IColumn, DetailsRow } from '@fluentui/react/lib/DetailsList';
import { SelectionMode, Selection, SelectionZone } from '@fluentui/react/lib/Selection';
import { Persona, PersonaSize } from '@fluentui/react/lib/Persona';
import { HttpMethod, useAuthApiCall } from '../../hooks/useAuthApiCall';
import { APIError } from '../../models/exceptions';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { LoadingState } from '../../models/loadingState';
import { ExceptionLayout } from '../shared/ExceptionLayout';
import { User } from '../../models/user';
import { AppRolesContext } from '../../contexts/AppRolesContext';

import { CommandBarButton, DefaultButton, Dialog, DialogFooter, getTheme, Spinner, SpinnerSize, Stack } from '@fluentui/react';
import { useNavigate, Route, Routes } from 'react-router-dom';
import { destructiveButtonStyles } from '../../styles';
import { WorkSpaceUsersAssignNew } from './WorkspaceUsersAssignNew';
import config from "../../config.json"

interface IUser {
  id: string;
  user_id: string;
  key: string;
  displayName: string;
  userPrincipalName: string;
  role: IUserRole;
  roles: IUserRole[];
}

interface IUserRole {
  id: string;
  displayName: string;
  type: string;
}

export const WorkspaceUsers: React.FunctionComponent = () => {
  const [state, setState] = useState({
    users: [] as IUser[],
    apiError: undefined as APIError | undefined,
    loadingState: LoadingState.Loading,
  });

  const [selectedUserRole, setSelectedUserRole] = useState<IUser | undefined>(undefined);
  const [hideCancelDialog, setHideCancelDialog] = useState(true);
  const [deassigning, setDeassigning] = useState(false);
  const [deassignmentError, setDeassignmentError] = useState(false);
  const [apiError, setApiError] = useState({} as APIError);

  const appRolesCtx = useContext(AppRolesContext);
  const [isTreAdmin, setIsTreAdmin] = useState(false);

  useEffect(() => {
    setIsTreAdmin(appRolesCtx.roles.includes('TREAdmin'));
  }, [appRolesCtx.roles]);

  const navigate = useNavigate();
  const theme = getTheme();
  const apiCall = useAuthApiCall();
  const { workspace, roles, workspaceApplicationIdURI } = useContext(WorkspaceContext);

  const [loadingUsers, setloadingUsers] = useState(false);

  const allowUserManagement = useMemo(() => {
    return isTreAdmin
      && config.userManagementEnabled
      && (workspace.properties['create_aad_groups'] === 'true' || workspace.properties['create_aad_groups'] === true);
  }, [isTreAdmin, workspace]);

  const getUsers = useCallback(async () => {
    setState((prevState) => ({
      ...prevState,
      apiError: undefined,
      loadingState: LoadingState.Loading,
    }));

    setloadingUsers(true);
    try {
      const scopeId = roles.length > 0 ? workspaceApplicationIdURI : "";
      const result = await apiCall(
        `${ApiEndpoint.Workspaces}/${workspace.id}/${ApiEndpoint.Users}`,
        HttpMethod.Get,
        scopeId,
      );

      const users = result.users
        .flatMap((user: any) =>
          user.roles.map((role: any) => ({
            id: `${user.id}__${role.id}`,
            user_id: user.id,
            displayName: user.displayName,
            userPrincipalName: user.userPrincipalName,
            role: role,
            roles: user.roles,
          })),
        )
        .sort((a: { role: any }, b: { role: any }) =>
          a.role.id.localeCompare(b.role.id),
        );

      setState({ users, apiError: undefined, loadingState: LoadingState.Ok });
    } catch (err: any) {
      err.userMessage = "Error retrieving users";
      setState({ users: [], apiError: err, loadingState: LoadingState.Error });
    }
    setloadingUsers(false);
  }, [apiCall, workspace.id, roles.length, workspaceApplicationIdURI]);

  const addedAssignment = async () => {
    navigate(-1);
    await getUsers();
  }

  useEffect(() => {
    getUsers();
  }, [getUsers]);

  // De-assign user from role
  const deassignUser = useCallback(async () => {
    try {
      setDeassigning(true);

      await apiCall(`${ApiEndpoint.Workspaces}/${workspace.id}/${ApiEndpoint.Users}/assign?user_id=${selectedUserRole?.user_id}&role_id=${selectedUserRole?.role.id}`,
        HttpMethod.Delete, "");

      await getUsers();


      setSelectedUserRole(undefined);
      setHideCancelDialog(true);
      setDeassigning(false);

    } catch (err: any) {
      err.userMessage = 'Error deassigning user';
      setApiError(err);
      setDeassignmentError(true);
      setDeassigning(false);
    }
  }, [apiCall, selectedUserRole, workspace.id, getUsers]);

  const groups: IGroup[] = useMemo(() => {
    const groupMap: any = {};
    const groups: any = [];
    let currentIndex = 0;

    state.users.forEach(user => {
      if (!groupMap[user.role.id]) {
        groupMap[user.role.id] = {
          count: 0,
          key: user.role.id,
          name: user.role.displayName,
          startIndex: currentIndex,
          level: 0
        };

        groups.push(groupMap[user.role.id]);
      }

      groupMap[user.role.id].count += 1;
      currentIndex += 1;
    });

    return groups;
  }, [state.users]);

  const selection = useMemo(() => {
    const s = new Selection({
      onSelectionChanged: () => {
        setSelectedUserRole(s.getSelection()[0] as IUser);
      }
    });
    s.setItems(state.users, true);
    return s;
  }, [state.users]);

  const columns: IColumn[] = useMemo(() => [
    {
      key: "name",
      name: "Name",
      fieldName: "name",
      minWidth: 150,
      onRender: (item: IUser) => (
        <Persona
          text={item.displayName}
          secondaryText={item.userPrincipalName}
          size={PersonaSize.size40}
          imageAlt={item.displayName}
        />
      )
    }
  ], []);

  const onRenderCell = React.useCallback(
    (nestingDepth?: number, item?: User, itemIndex?: number, group?: IGroup): React.ReactNode => (
      <DetailsRow
        columns={columns}
        groupNestingDepth={nestingDepth}
        item={item}
        itemIndex={itemIndex!}
        selection={selection}
        selectionMode={allowUserManagement ? SelectionMode.single : SelectionMode.none}
        group={group}
      />
    ),
    [columns, selection, isTreAdmin],
  );

  return (
    <>
      <Stack className="tre-panel">
        <Stack.Item>
          <Stack horizontal horizontalAlign="space-between">
            <h1 style={{ marginBottom: 0, marginRight: 30 }}>Users</h1>
            {allowUserManagement &&
              <Stack horizontal horizontalAlign="start">
                <CommandBarButton
                  iconProps={{ iconName: 'add' }}
                  text="Assign New"
                  style={{ background: 'none', color: theme.palette.themePrimary }}
                  onClick={() => navigate('new')}
                />
                {
                  selectedUserRole &&
                  <CommandBarButton
                    iconProps={{ iconName: 'delete' }}
                    text="De-assign"
                    style={{ background: 'none', color: theme.palette.themePrimary }}
                    onClick={() => {
                      console.log('De-assign', selectedUserRole);
                      setHideCancelDialog(false);
                    }}
                  />
                }
              </Stack>
            }
          </Stack>
        </Stack.Item>
      </Stack>
      {state.apiError && <ExceptionLayout e={state.apiError} />}
      <div className="tre-resource-panel" style={{ padding: '0px' }}>
        {!loadingUsers && <SelectionZone selection={selection} selectionMode={isTreAdmin ? SelectionMode.single : SelectionMode.none} >
          <GroupedList
            items={state.users}
            onRenderCell={onRenderCell}
            selectionMode={SelectionMode.none}
            selection={selection}
            groups={groups}
            compact={false}
          />
        </SelectionZone>
        }
      </div>
      {
        loadingUsers && <Stack>
          <Stack.Item style={{ paddingTop: '10px', paddingBottom: '10px' }}>
            <Spinner />
          </Stack.Item>
        </Stack>
      }
      <Dialog
        hidden={hideCancelDialog}
        onDismiss={() => { setHideCancelDialog(true); }}
        dialogContentProps={{
          title: 'De-assign Role?',
          subText: `Are you sure you want to remove ${selectedUserRole?.displayName} from the ${selectedUserRole?.role.displayName} Role?`,
        }}
      >
        {
          deassignmentError && <ExceptionLayout e={apiError} />
        }
        {
          deassigning
            ? <Spinner label="Submitting..." ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
            : <DialogFooter>
              <DefaultButton onClick={deassignUser} text="De-assign User" styles={destructiveButtonStyles} />
              <DefaultButton onClick={() => { setHideCancelDialog(true); }} text="Back" />
            </DialogFooter>
        }
      </Dialog>

      <Routes>
        <Route path="new" element={
          <WorkSpaceUsersAssignNew onAssignUser={addedAssignment} />
        } />
      </Routes>
    </>
  );
};

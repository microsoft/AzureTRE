import * as React from 'react';
import { useState, useCallback, useEffect, useMemo, useContext } from 'react';
import { GroupedList, IGroup } from '@fluentui/react/lib/GroupedList';
import { IColumn, DetailsRow } from '@fluentui/react/lib/DetailsList';
import { SelectionMode } from '@fluentui/react/lib/Selection';
import { Persona, PersonaSize } from '@fluentui/react/lib/Persona';
import { HttpMethod, useAuthApiCall } from '../../hooks/useAuthApiCall';
import { APIError } from '../../models/exceptions';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { LoadingState } from '../../models/loadingState';
import { ExceptionLayout } from '../shared/ExceptionLayout';
import { User } from '../../models/user';
import { Stack } from '@fluentui/react';

interface IUser {
  id: string;
  name: string;
  email: string;
  role: IGroup;
  roles: string[];
}

export const WorkspaceUsers: React.FunctionComponent = () => {
  const [state, setState] = useState({
    users: [] as User[],
    apiError: undefined as APIError | undefined,
    loadingState: LoadingState.Loading,
  });

  const apiCall = useAuthApiCall();
  const { workspace, roles, workspaceApplicationIdURI } = useContext(WorkspaceContext);

  const getUsers = useCallback(async () => {
    setState(prevState => ({ ...prevState, apiError: undefined, loadingState: LoadingState.Loading }));

    try {
      const scopeId = roles.length > 0 ? workspaceApplicationIdURI : "";
      const result = await apiCall(`${ApiEndpoint.Workspaces}/${workspace.id}/${ApiEndpoint.Users}`, HttpMethod.Get, scopeId);

      const users = result.users.flatMap((user: any) =>
        user.roles.map((role: string) => ({
          id: user.id,
          name: user.name,
          email: user.email,
          role: role,
          roles: user.roles
        }))
      ).sort((a: { role: string; }, b: { role: string; }) => a.role.localeCompare(b.role));

      setState({ users, apiError: undefined, loadingState: LoadingState.Ok });
    } catch (err: any) {
      err.userMessage = "Error retrieving users";
      setState({ users: [], apiError: err, loadingState: LoadingState.Error });
    }
  }, [apiCall, workspace.id, roles.length, workspaceApplicationIdURI]);

  useEffect(() => {
    getUsers();
  }, [getUsers]);

  const groupedUsers = useMemo(() => {
    const groups: { [key: string]: User[] } = {};
    state.users.forEach(user => {
      user.roles.forEach(role => {
        if (!groups[role]) {
          groups[role] = [];
        }
        groups[role].push(user);
      });
    });
    return groups;
  }, [state.users]);

  const groups: IGroup[] = useMemo(() => {
    return Object.keys(groupedUsers).map((role, index) => ({
      key: role,
      name: role,
      startIndex: index,
      count: groupedUsers[role].length,
    }));
  }, [groupedUsers]);


  const columns: IColumn[] = [
    {
      key: 'name',
      name: 'Name',
      fieldName: 'name',
      minWidth: 150,
      onRender: (item: User) => (
        <Persona
          text={item.name}
          secondaryText={item.email}
          size={PersonaSize.size40}
          imageAlt={item.name}
        />
      ),
    }
  ];

  const onRenderCell = (
    nestingDepth?: number,
    item?: IUser,
    itemIndex?: number,
    group?: IGroup,
  ): React.ReactNode => {
    return item && typeof itemIndex === 'number' && itemIndex > -1 ? (
      <DetailsRow
        columns={columns}
        groupNestingDepth={nestingDepth}
        item={item}
        itemIndex={itemIndex}
        selectionMode={SelectionMode.none}
        compact={false}
        group={group}
      />
    ) : null;
  };

  return (
    <>
      <Stack className="tre-panel">
        <Stack.Item>
          <Stack horizontal horizontalAlign="space-between">
            <h1 style={{ marginBottom: 0, marginRight: 30 }}>Users</h1>
          </Stack>
        </Stack.Item>
      </Stack>
      {state.apiError && <ExceptionLayout e={state.apiError} />}
      <div className="tre-resource-panel" style={{ padding: '0px' }}>
        <GroupedList
          items={state.users}
          onRenderCell={onRenderCell}
          selectionMode={SelectionMode.none}
          groups={groups}
          compact={false}
        />
      </div>
    </>
  );
}

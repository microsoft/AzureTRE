import React, { useEffect, useState } from 'react';
import { DetailsList, DetailsListLayoutMode, IColumn } from '@fluentui/react/lib/DetailsList';
import { getWorkspaceUsers } from '../../services/workspaceService';

interface User {
  name: string;
  email: string;
  roles: string[];
}

const columns: IColumn[] = [
  { key: 'name', name: 'Name', fieldName: 'name', minWidth: 100, maxWidth: 200, isResizable: true },
  { key: 'email', name: 'Email', fieldName: 'email', minWidth: 100, maxWidth: 200, isResizable: true },
  { key: 'roles', name: 'Roles', fieldName: 'roles', minWidth: 100, maxWidth: 200, isResizable: true }
];

export const WorkspaceUsers: React.FunctionComponent = () => {
  const [users, setUsers] = useState<User[]>([]);

  useEffect(() => {
    const fetchUsers = async () => {
      const users = await getWorkspaceUsers();
      setUsers(users);
    };

    fetchUsers();
  }, []);

  return (
    <DetailsList
      items={users}
      columns={columns}
      setKey="set"
      layoutMode={DetailsListLayoutMode.justified}
      isHeaderVisible={true}
    />
  );
};

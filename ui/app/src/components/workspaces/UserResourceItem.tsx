import React from 'react';
import { useParams } from 'react-router-dom';
import { Workspace } from '../../models/workspace';

interface UserResourceItemProps {
  workspace: Workspace
}

export const UserResourceItem: React.FunctionComponent<UserResourceItemProps> = (props:UserResourceItemProps) => {
  const { userResourceId } = useParams();

  return (
    <>
      <h1>User Resource: {userResourceId}</h1>
    </>
  );
};

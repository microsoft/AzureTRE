import React from 'react';
import { useParams } from 'react-router-dom';

export const UserResourceItem: React.FunctionComponent = () => {
  const { userResourceId } = useParams();

  return (
    <>
      <h1>User Resource: {userResourceId}</h1>
    </>
  );
};

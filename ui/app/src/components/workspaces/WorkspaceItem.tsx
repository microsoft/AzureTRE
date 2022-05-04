import React from 'react';
import { Outlet, useParams } from 'react-router-dom';

export const WorkspaceItem: React.FunctionComponent = () => {
  const { workspaceId } = useParams();

  return (
    <>
      <h1>Workspace {workspaceId}</h1>
      <Outlet />
    </>
  );
};

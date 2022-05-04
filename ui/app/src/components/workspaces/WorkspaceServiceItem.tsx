import React from 'react';
import { Link, Outlet, useParams } from 'react-router-dom';

export const WorkspaceServiceItem: React.FunctionComponent = () => {
  const { workspaceServiceId } = useParams();

  return (
    <>
      <h1>Workspace Service: {workspaceServiceId}</h1>
      <Link to='user-resources/abcd'>VM 1</Link>
      <Link to='user-resources/efgh'>VM 2</Link>

      <Outlet />
    </>
  );
};

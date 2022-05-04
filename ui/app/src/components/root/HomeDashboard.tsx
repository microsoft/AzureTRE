import React from 'react';
import { Link } from 'react-router-dom';

export const HomeDashboard: React.FunctionComponent = () => {
  return(
  <>
    <h1>Workspaces</h1>
    <Link to='/workspaces/187654-76543-65432'>Workspace 1</Link> <br />
    <Link to='/workspaces/6543-76543-6543-543'>Workspace 2</Link> <br />
  </>
  );
};

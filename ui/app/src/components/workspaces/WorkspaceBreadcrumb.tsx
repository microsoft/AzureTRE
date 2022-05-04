import React from 'react';
import { getTheme, mergeStyles } from '@fluentui/react';
import { Link } from 'react-router-dom';
import { useLocation } from 'react-router-dom';


export const WorkspaceBreadcrumb: React.FunctionComponent = () => {
  const path = useLocation().pathname

  let parts = path.split('/')
  let workspaceId = parts[2]
  let workspaceServiceId = parts[4] || ''
  let userResourceId = parts[6] || ''

  return (
    <div className={contentClass}>
      <Link to='/'>Dashboard</Link>
      &gt;
      <Link to={'/workspaces/' + workspaceId}>{workspaceId}</Link>
      
      {
        workspaceServiceId && (
          <>
            &gt;
            <Link to={'/workspaces/' + workspaceId + '/workspace-services/' + workspaceServiceId}>{workspaceServiceId}</Link>
          </>
        )
      }

      {
        userResourceId && (
          <>
             &gt;
            <Link to={'/workspace-services/' + workspaceServiceId + '/user-resources/' + userResourceId}>{userResourceId}</Link>
          </>
        )}
    </div>
  );
};

const theme = getTheme();
const contentClass = mergeStyles([
  {
    backgroundColor: theme.palette.white,
    color: theme.palette.themePrimary,
    lineHeight: '20px',
    padding: '0 20px',
  }
]);
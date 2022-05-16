import React, { useContext } from 'react';
import { WorkspaceRolesContext } from '../workspaces/WorkspaceRolesContext';
import { RootRolesContext } from './RootRolesContext';

interface SecuredByRoleProps {
  element: JSX.Element,
  workspaceAuth?: boolean,
  allowedRoles: Array<string>
}

// Check if the user roles match any of the roles we are given - if they do, show the element, if not, don't
export const SecuredByRole: React.FunctionComponent<SecuredByRoleProps> = (props: SecuredByRoleProps) => {
  const rootRoles = useContext(RootRolesContext); // the user is in these roles which apply across the app
  const workspaceRoles = useContext(WorkspaceRolesContext); // the user is in these roles for the currently selected workspace

  const userRoles = props.workspaceAuth ? workspaceRoles.roles : rootRoles.roles;

  if (userRoles && userRoles.length > 0)
  {
    let intersection = props.allowedRoles.filter(x => userRoles.includes(x));

    if (intersection.length > 0){
      return props.element
    }
  }
  
  return (<></>);
};

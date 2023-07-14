import React, { useContext } from 'react';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import { AppRolesContext } from '../../contexts/AppRolesContext';
import { MessageBar, MessageBarType } from '@fluentui/react';

interface SecuredByRoleProps {
  element: JSX.Element,
  workspaceAuth?: boolean,
  allowedRoles: Array<string>,
  errorString?: String
}

// Check if the user roles match any of the roles we are given - if they do, show the element, if not, don't
export const SecuredByRole: React.FunctionComponent<SecuredByRoleProps> = (props: SecuredByRoleProps) => {
  const appRoles = useContext(AppRolesContext); // the user is in these roles which apply across the app
  const workspaceCtx = useContext(WorkspaceContext); // the user is in these roles for the currently selected workspace

  const userRoles = props.workspaceAuth ? workspaceCtx.roles : appRoles.roles;

  if (userRoles && userRoles.length > 0) {
    let intersection = props.allowedRoles.filter(x => userRoles.includes(x));

    if (intersection.length > 0) {
      return props.element
    }
  }

  return (props.errorString ?
    <MessageBar
      messageBarType={MessageBarType.error}
      isMultiline={true}
    >
      <h3>Access Denied</h3>
      <p>{props.errorString}</p>
    </MessageBar>
    : <></>);
};

import React, { useContext, useEffect, useState } from 'react';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import { AppRolesContext } from '../../contexts/AppRolesContext';
import { MessageBar, MessageBarType } from '@fluentui/react';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { HttpMethod, ResultType, useAuthApiCall } from '../../hooks/useAuthApiCall';

interface SecuredByRoleProps {
  element: JSX.Element,
  allowedAppRoles?: Array<string>,
  allowedWorkspaceRoles?: Array<string>,
  workspaceId?: string,
  errorString?: String;
}

// Check if the user roles match any of the roles we are given - if they do, show the element, if not, don't
export const SecuredByRole: React.FunctionComponent<SecuredByRoleProps> = (props: SecuredByRoleProps) => {
  const apiCall = useAuthApiCall();

  const appRoles = useContext(AppRolesContext);
  const workspaceCtx = useContext(WorkspaceContext);
  const [workspaceRoles, setRoles] = useState([] as Array<string>);

  useEffect(() => {
    const getWorkspaceRoles = async () => {
      if (!workspaceCtx.workspace.id && props.workspaceId !== "") {
        let r = [] as Array<string>;

        let workspaceAuth = (await apiCall(`${ApiEndpoint.Workspaces}/${props.workspaceId}/scopeid`, HttpMethod.Get)).workspaceAuth;
        if (workspaceAuth) {
          await apiCall(`${ApiEndpoint.Workspaces}/${props.workspaceId}`, HttpMethod.Get, workspaceAuth.scopeId,
            undefined, ResultType.JSON, (roles: Array<string>) => {
              r = roles;
            }, true);
        }
        setRoles(r);
      }
    };

    if (workspaceCtx.roles.length === 0 && props.workspaceId !== undefined) {
      getWorkspaceRoles();
    }
    else {
      setRoles(workspaceCtx.roles);
    }

  }, [apiCall, workspaceCtx.workspace.id, props.workspaceId, workspaceCtx.roles]);

  return (
    (workspaceRoles?.some(x => props.allowedWorkspaceRoles?.includes(x)) || appRoles?.roles?.some(x => props.allowedAppRoles?.includes(x)))
      ? props.element
      : (props.errorString && (workspaceRoles.length > 0 || appRoles.roles.length > 0)
          ? <MessageBar messageBarType={MessageBarType.error} isMultiline={true}>
              <h3>Access Denied</h3>
              <p>{props.errorString}</p>
            </MessageBar>
          : null)
  );
};

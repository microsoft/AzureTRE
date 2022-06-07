import React, { useContext, useEffect, useState } from 'react';
import { Route, Routes, useNavigate, useParams } from 'react-router-dom';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { useAuthApiCall, HttpMethod } from '../../hooks/useAuthApiCall';
import { UserResource } from '../../models/userResource';
import { WorkspaceService } from '../../models/workspaceService';
import { MessageBar, MessageBarType, PrimaryButton, Spinner, SpinnerSize, Stack } from '@fluentui/react';
import { ComponentAction, Resource } from '../../models/resource';
import { ResourceCardList } from '../shared/ResourceCardList';
import { LoadingState } from '../../models/loadingState';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';
import { ResourceType } from '../../models/resourceType';
import { ResourceHeader } from '../shared/ResourceHeader';
import { useComponentManager } from '../../hooks/useComponentManager';
import { CreateUpdateResourceContext } from '../../contexts/CreateUpdateResourceContext';
import { successStates } from '../../models/operation';
import { UserResourceItem } from './UserResourceItem';
import { ResourceBody } from '../shared/ResourceBody';

interface WorkspaceServiceItemProps {
  workspaceService?: WorkspaceService,
  updateWorkspaceService: (ws: WorkspaceService) => void,
  removeWorkspaceService: (ws: WorkspaceService) => void
}

export const WorkspaceServiceItem: React.FunctionComponent<WorkspaceServiceItemProps> = (props: WorkspaceServiceItemProps) => {
  const { workspaceServiceId } = useParams();
  const [userResources, setUserResources] = useState([] as Array<UserResource>)
  const [workspaceService, setWorkspaceService] = useState({} as WorkspaceService)
  const [loadingState, setLoadingState] = useState(LoadingState.Loading);
  const [selectedUserResource, setSelectedUserResource] = useState({} as UserResource);
  const [hasUserResourceTemplates, setHasUserResourceTemplates] = useState(false);
  const workspaceCtx = useContext(WorkspaceContext);
  const createFormCtx = useContext(CreateUpdateResourceContext);
  const navigate = useNavigate();
  const apiCall = useAuthApiCall();
  const latestUpdate = useComponentManager(
    workspaceService,
    (r: Resource) => { props.updateWorkspaceService(r as WorkspaceService); setWorkspaceService(r as WorkspaceService) },
    (r: Resource) => { props.removeWorkspaceService(r as WorkspaceService); navigate(`/${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.WorkspaceServices}`) }
  );

  useEffect(() => {
    const getData = async () => {
      setHasUserResourceTemplates(false);
      try {
        let svc = props.workspaceService || {} as WorkspaceService;
        // did we get passed the workspace service, or shall we get it from the api?
        if (props.workspaceService && props.workspaceService.id && props.workspaceService.id === workspaceServiceId) {
          setWorkspaceService(props.workspaceService);
        } else {
          let ws = await apiCall(`${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.WorkspaceServices}/${workspaceServiceId}`, HttpMethod.Get, workspaceCtx.workspaceClientId);
          setWorkspaceService(ws.workspaceService);
          svc = ws.workspaceService;
        }

        // get the user resources
        const u = await apiCall(`${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.WorkspaceServices}/${workspaceServiceId}/${ApiEndpoint.UserResources}`, HttpMethod.Get, workspaceCtx.workspaceClientId)

        // get user resource templates - to check
        const ut = await apiCall(`${ApiEndpoint.WorkspaceServiceTemplates}/${svc.templateName}/${ApiEndpoint.UserResourceTemplates}`, HttpMethod.Get);
        setHasUserResourceTemplates(ut && ut.templates && ut.templates.length > 0);
        setUserResources(u.userResources);
        setLoadingState(LoadingState.Ok);
      } catch {
        setLoadingState(LoadingState.Error);
      }
    };
    getData();
  }, [apiCall, props.workspaceService, workspaceCtx.workspace.id, workspaceCtx.workspaceClientId, workspaceServiceId]);

  const addUserResource = (u: UserResource) => {
    let ur = [...userResources];
    ur.push(u);
    setUserResources(ur);
  }

  const updateUserResource = (u: UserResource) => {
    let ur = [...userResources];
    let i = ur.findIndex((f: UserResource) => f.id === u.id);
    ur.splice(i, 1, u);
    setUserResources(ur);
  }

  const removeUserResource = (u: UserResource) => {
    let ur = [...userResources];
    let i = ur.findIndex((f: UserResource) => f.id === u.id);
    ur.splice(i, 1);
    setUserResources(ur);
  }

  switch (loadingState) {
    case LoadingState.Ok:
      return (
        <>
          <Routes>
            <Route path="*" element={
              <>
                <ResourceHeader resource={workspaceService} latestUpdate={latestUpdate} />
                <ResourceBody resource={workspaceService} />

                {
                  hasUserResourceTemplates &&
                  <Stack className="tre-panel">
                    <Stack.Item>
                      <Stack horizontal horizontalAlign="space-between">
                        <h1>User Resources</h1>
                        <PrimaryButton iconProps={{ iconName: 'Add' }} text="Create new" disabled={!workspaceService.isEnabled || latestUpdate.componentAction === ComponentAction.Lock || successStates.indexOf(workspaceService.deploymentStatus) === -1} title={!workspaceService.isEnabled ? 'Service must be enabled first' : 'Create a User Resource'}
                          onClick={() => {
                            createFormCtx.openCreateForm({
                              resourceType: ResourceType.UserResource,
                              resourceParent: workspaceService,
                              onAdd: (r: Resource) => addUserResource(r as UserResource),
                              workspaceClientId: workspaceCtx.workspaceClientId
                            })
                          }} />
                      </Stack>
                    </Stack.Item>
                    <Stack.Item>
                      {
                        userResources &&
                        <ResourceCardList
                          resources={userResources}
                          selectResource={(r: Resource) => setSelectedUserResource(r as UserResource)}
                          updateResource={(r: Resource) => updateUserResource(r as UserResource)}
                          removeResource={(r: Resource) => removeUserResource(r as UserResource)}
                          emptyText="This workspace service contains no user resources." />
                      }
                    </Stack.Item>
                  </Stack>
                }
              </>
            } />
            <Route path="user-resources/:userResourceId/*" element={
              <UserResourceItem
                userResource={selectedUserResource}
                updateUserResource={(u: UserResource) => updateUserResource(u)}
                removeUserResource={(u: UserResource) => removeUserResource(u)}
              />
            } />
          </Routes>

        </>
      );
    case LoadingState.Error:
      return (
        <MessageBar
          messageBarType={MessageBarType.error}
          isMultiline={true}
        >
          <h3>Error retrieving workspace</h3>
          <p>There was an error retrieving this workspace. Please see the browser console for details.</p>
        </MessageBar>
      );
    default:
      return (
        <div style={{ marginTop: '20px' }}>
          <Spinner label="Loading Workspace Service" ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
        </div>
      )
  }
};

import { Icon, mergeStyles, Panel, PanelType, PrimaryButton } from '@fluentui/react';
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiEndpoint } from '../../../models/apiEndpoints';
import { Operation } from '../../../models/operation';
import { ResourceType } from '../../../models/resourceType';
import { Workspace } from '../../../models/workspace';
import { WorkspaceService } from '../../../models/workspaceService';
import { ResourceForm } from './ResourceForm';
import { SelectTemplate } from './SelectTemplate';
import { getResourceFromResult, Resource } from '../../../models/resource';
import { HttpMethod, useAuthApiCall } from '../../../hooks/useAuthApiCall';
import { useAppDispatch } from '../../../hooks/customReduxHooks';
import { addUpdateOperation } from '../../shared/notifications/operationsSlice';

interface CreateUpdateResourceProps {
  isOpen: boolean,
  onClose: () => void,
  workspaceApplicationIdURI?: string,
  resourceType: ResourceType,
  parentResource?: Workspace | WorkspaceService,
  onAddResource?: (r: Resource) => void,
  updateResource?: Resource
}

interface PageTitle {
  selectTemplate: string,
  resourceForm: string,
  creating: string
}

const creatingIconClass = mergeStyles({
  fontSize: 100,
  height: 100,
  width: 100,
  margin: '0 25px',
  color: 'deepskyblue',
  padding: 20
});

export const CreateUpdateResource: React.FunctionComponent<CreateUpdateResourceProps> = (props: CreateUpdateResourceProps) => {
  const [page, setPage] = useState('selectTemplate' as keyof PageTitle);
  const [selectedTemplate, setTemplate] = useState(props.updateResource?.templateName || '');
  const [deployOperation, setDeployOperation] = useState({} as Operation);
  const navigate = useNavigate();
  const apiCall = useAuthApiCall();
  const dispatch = useAppDispatch();

  useEffect(() => {
    const clearState = () => {
      setPage('selectTemplate');
      setDeployOperation({} as Operation);
      setTemplate('');
    }

    !props.isOpen && clearState();
    props.isOpen && props.updateResource && props.updateResource.templateName && selectTemplate(props.updateResource.templateName);
  }, [props.isOpen, props.updateResource]);

  // Render a panel title depending on sub-page
  const pageTitles: PageTitle = {
    selectTemplate: 'Choose a template',
    resourceForm: 'Create / Update a ' + props.resourceType,
    creating: ''
  }

  // Construct API paths for templates of specified resourceType
  let templateListPath;
  // Usually, the GET path would be `${templateGetPath}/${selectedTemplate}`, but there's an exception for user resources
  let templateGetPath;

  let workspaceApplicationIdURI = undefined
  switch (props.resourceType) {
    case ResourceType.Workspace:
      templateListPath = ApiEndpoint.WorkspaceTemplates; templateGetPath = templateListPath; break;
    case ResourceType.WorkspaceService:
      templateListPath = ApiEndpoint.WorkspaceServiceTemplates; templateGetPath = templateListPath; break;
    case ResourceType.SharedService:
      templateListPath = ApiEndpoint.SharedServiceTemplates; templateGetPath = templateListPath; break;
    case ResourceType.UserResource:
      if (props.parentResource) {
        // If we are creating a user resource, parent resource must have a workspaceId
        const workspaceId = (props.parentResource as WorkspaceService).workspaceId
        templateListPath = `${ApiEndpoint.Workspaces}/${workspaceId}/${ApiEndpoint.WorkspaceServiceTemplates}/${props.parentResource.templateName}/${ApiEndpoint.UserResourceTemplates}`;
        templateGetPath = `${ApiEndpoint.WorkspaceServiceTemplates}/${props.parentResource.templateName}/${ApiEndpoint.UserResourceTemplates}`
        workspaceApplicationIdURI = props.workspaceApplicationIdURI
        break;
      } else {
        throw Error('Parent workspace service must be passed as prop when creating user resource.');
      }
    default:
      throw Error('Unsupported resource type.');
  }

  // Construct API path for resource creation
  let resourcePath;
  switch (props.resourceType) {
    case ResourceType.Workspace:
      resourcePath = ApiEndpoint.Workspaces; break;
    case ResourceType.SharedService:
      resourcePath = ApiEndpoint.SharedServices; break;
    default:
      if (!props.parentResource) {
        throw Error('A parentResource must be passed as prop if creating a workspace-service or user-resource');
      }
      resourcePath = `${props.parentResource.resourcePath}/${props.resourceType}s`;
  }

  const selectTemplate = (templateName: string) => {
    setTemplate(templateName);
    setPage('resourceForm');
  }

  const resourceCreating = async (operation: Operation) => {
    setDeployOperation(operation);
    setPage('creating');
    // Add deployment operation to notifications operation poller
    dispatch(addUpdateOperation(operation));

    // if an onAdd callback has been given, get the resource we just created and pass it back
    if (props.onAddResource) {
      let resource = getResourceFromResult(await apiCall(operation.resourcePath, HttpMethod.Get, props.workspaceApplicationIdURI));
      props.onAddResource(resource);
    }
  }

  // Render the current panel sub-page
  let currentPage;
  switch (page) {
    case 'selectTemplate':
      currentPage = <SelectTemplate templatesPath={templateListPath} workspaceApplicationIdURI={workspaceApplicationIdURI} onSelectTemplate={selectTemplate} />; break;
    case 'resourceForm':
      currentPage = <ResourceForm
        templateName={selectedTemplate}
        templatePath={`${templateGetPath}/${selectedTemplate}`}
        resourcePath={resourcePath}
        onCreateResource={resourceCreating}
        workspaceApplicationIdURI={props.workspaceApplicationIdURI}
        updateResource={props.updateResource}
      />; break;
    case 'creating':
      currentPage = <div style={{ textAlign: 'center', paddingTop: 100 }}>
        <Icon iconName="CloudAdd" className={creatingIconClass} />
        <h1>{props.updateResource?.id ? 'Updating' : 'Creating'} {props.resourceType}...</h1>
        <p>Check the notifications panel for deployment progress.</p>
        <PrimaryButton text="Go to resource" onClick={() => {navigate(deployOperation.resourcePath); props.onClose();}} />
      </div>; break;
  }

  return (
    <>
      <Panel
        headerText={pageTitles[page]}
        isOpen={props.isOpen}
        onDismiss={props.onClose}
        type={PanelType.medium}
        closeButtonAriaLabel="Close"
        isLightDismiss
      >
        <div style={{ paddingTop: 30 }}>
          {currentPage}
        </div>
      </Panel>
    </>
  );
};

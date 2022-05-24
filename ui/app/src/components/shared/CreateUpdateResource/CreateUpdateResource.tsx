import { Icon, mergeStyles, Panel, PanelType, PrimaryButton } from '@fluentui/react';
import React, { useContext, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiEndpoint } from '../../../models/apiEndpoints';
import { Operation } from '../../../models/operation';
import { ResourceType } from '../../../models/resourceType';
import { Workspace } from '../../../models/workspace';
import { WorkspaceService } from '../../../models/workspaceService';
import { NotificationsContext } from '../../../contexts/NotificationsContext';
import { ResourceForm } from './ResourceForm';
import { SelectTemplate } from './SelectTemplate';

interface CreateUpdateResourceProps {
  isOpen: boolean,
  onClose: () => void,
  resourceType: ResourceType,
  parentResource?: Workspace | WorkspaceService
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
  const [selectedTemplate, setTemplate] = useState('');
  const [deployOperation, setDeployOperation] = useState({} as Operation);
  const opsContext = useContext(NotificationsContext);
  const navigate = useNavigate();

  useEffect(() => {
    const clearState = () => {
      setPage('selectTemplate');
      setDeployOperation({} as Operation);
      setTemplate('');
    }

    // Clear state on panel close
    if (!props.isOpen) {
      clearState();
    }
  }, [props.isOpen]);

  // Render a panel title depending on sub-page
  const pageTitles: PageTitle = {
    selectTemplate: 'Choose a template',
    resourceForm: 'Create a new ' + props.resourceType,
    creating: ''
  }

  // Construct API path for templates of specified resourceType
  let templatesPath;
  switch (props.resourceType) {
    case ResourceType.Workspace:
      templatesPath = ApiEndpoint.WorkspaceTemplates; break;
    case ResourceType.WorkspaceService:
      templatesPath = ApiEndpoint.WorkspaceServiceTemplates; break;
    case ResourceType.SharedService:
      templatesPath = ApiEndpoint.SharedServiceTemplates; break;
    case ResourceType.UserResource:
      if (props.parentResource) {
        templatesPath = `${ApiEndpoint.WorkspaceServiceTemplates}/${props.parentResource.templateName}/${ApiEndpoint.UserResourceTemplates}`; break;
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
      resourcePath = `${props.parentResource.resourcePath}/${props.resourceType}`;
  }

  const selectTemplate = (templateName: string) => {
    setTemplate(templateName);
    setPage('resourceForm');
  }

  const resourceCreating = (operation: Operation) => {
    setDeployOperation(operation);
    setPage('creating');
    // Add deployment operation to notifications operation poller
    opsContext.addOperations([operation]);
  }

  // Render the current panel sub-page
  let currentPage;
  switch(page) {
    case 'selectTemplate':
      currentPage = <SelectTemplate templatesPath={templatesPath} onSelectTemplate={selectTemplate}/>; break;
    case 'resourceForm':
      currentPage = <ResourceForm 
        templateName={selectedTemplate}
        templatePath={`${templatesPath}/${selectedTemplate}`}
        resourcePath={resourcePath}
        onCreateResource={resourceCreating}
      />; break;
    case 'creating':
      currentPage = <div style={{ textAlign: 'center', paddingTop: 100 }}>
        <Icon iconName="CloudAdd" className={creatingIconClass} />
        <h1>Creating {props.resourceType}...</h1>
        <p>Check the notifications panel for deployment progress.</p>
        <PrimaryButton text="Go to resource" onClick={() => navigate(deployOperation.resourcePath)}/>
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
      >
        { currentPage }
      </Panel>
    </>
  );
};

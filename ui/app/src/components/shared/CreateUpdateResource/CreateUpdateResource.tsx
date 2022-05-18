import { DefaultButton, Icon, mergeStyles, Panel, PanelType, PrimaryButton } from '@fluentui/react';
import { useBoolean } from '@fluentui/react-hooks';
import React, { useEffect, useState } from 'react';
import { ApiEndpoint } from '../../../models/apiEndpoints';
import { ResourceType } from '../../../models/resourceType';
import { ResourceForm } from './ResourceForm';
import { SelectTemplate } from './SelectTemplate';

interface CreateUpdateResourceProps {
  resourceType: ResourceType,
  serviceName?: string
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
  const [isOpen, { setTrue: openPanel, setFalse: dismissPanel }] = useBoolean(false);
  const [page, setPage] = useState('selectTemplate' as keyof PageTitle);
  const [selectedTemplate, setTemplate] = useState('');

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
      case ResourceType.UserResource:
        if (props.serviceName) {
          templatesPath = `${ApiEndpoint.WorkspaceServiceTemplates}/${props.serviceName}/${ApiEndpoint.UserResourceTemplates}`; break;
        } else {
          throw Error('serviceTemplateName must also be passed for workspace-service resourceType.');
        }
      default:
        throw Error('Unsupported resource type.');
  }

  const selectTemplate = (templateName: string) => {
    setTemplate(templateName);
    setPage('resourceForm');
  }

  const createResource = (resource: {}) => {
    console.log('Creating resource...', resource);
    setPage('creating');
  }

  // Render the current panel sub-page
  let currentPage;
  switch(page) {
    case 'selectTemplate':
      currentPage = <SelectTemplate templatesPath={templatesPath} onSelectTemplate={selectTemplate}/>; break;
    case 'resourceForm':
      currentPage = <ResourceForm templatePath={`${templatesPath}/${selectedTemplate}`} createResource={createResource}/>; break;
    case 'creating':
      currentPage = <div style={{ textAlign: 'center', paddingTop: 100 }}>
        <Icon iconName="CloudAdd" className={creatingIconClass} />
        <h1>Creating {props.resourceType}</h1>
        <p>Check the notifications panel for deployment progress.</p>
        <DefaultButton text="Exit" onClick={dismissPanel} style={{ marginTop: 25 }}/>
      </div>; break;
  }

  useEffect(() => {
    const clearState = () => {
      setPage('selectTemplate');
      setTemplate('');
    }

    // Clear state on panel close
    if (!isOpen) {
      clearState();
    }
  });

  return (
    <>
      <PrimaryButton iconProps={{ iconName: 'Add' }} text="Create new" onClick={openPanel} />
      <Panel
        headerText={pageTitles[page]}
        isOpen={isOpen}
        onDismiss={dismissPanel}
        type={PanelType.medium}
        closeButtonAriaLabel="Close"
      >
        { currentPage }
      </Panel>
    </>
  );
};

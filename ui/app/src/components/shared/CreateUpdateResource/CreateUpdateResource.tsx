import { Panel, PanelType, PrimaryButton } from '@fluentui/react';
import { useBoolean } from '@fluentui/react-hooks';
import React, { useEffect, useState } from 'react';
import { ResourceType } from '../../../models/resourceType';
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

export const CreateUpdateResource: React.FunctionComponent<CreateUpdateResourceProps> = (props: CreateUpdateResourceProps) => {
  const [isOpen, { setTrue: openPanel, setFalse: dismissPanel }] = useBoolean(false);
  const [page, setPage] = useState('selectTemplate' as keyof PageTitle);
  const pageTitles: PageTitle = {
    selectTemplate: 'Choose a template',
    resourceForm: 'Create a new ' + props.resourceType,
    creating: ''
  }

  const selectTemplate = (templateName: string) => {
    setPage('resourceForm');
  }

  // Render the current page
  let currentPage;
  switch(page) {
    case 'selectTemplate':
      currentPage = <SelectTemplate resourceType={props.resourceType} serviceName={props.serviceName} onSelectTemplate={selectTemplate}/>; break;
    case 'resourceForm':
      currentPage = <p>This is a form</p>; break;
    case 'creating':
      currentPage = <p>Creating...</p>; break;
  }

  useEffect(() => {
    const clearState = () => {
      setPage('selectTemplate');
    }

    // Clear state on panel close
    if (!isOpen) {
      clearState();
    }
  });

  return (
    <>
      <PrimaryButton text="Create new" onClick={openPanel} />
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

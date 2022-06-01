import React, { useEffect, useState } from 'react';
import { Resource } from '../../models/resource';
import { ResourceCardList } from '../shared/ResourceCardList';
import { useBoolean } from '@fluentui/react-hooks';
import { PrimaryButton, Stack } from '@fluentui/react';
import { CreateUpdateResource } from '../shared/CreateUpdateResource/CreateUpdateResource';
import { ResourceType } from '../../models/resourceType';
import { SharedService } from '../../models/sharedService';
import { HttpMethod, useAuthApiCall } from '../../hooks/useAuthApiCall';
import { ApiEndpoint } from '../../models/apiEndpoints';

export const SharedServices: React.FunctionComponent = () => {
  const [createPanelOpen, { setTrue: createNew, setFalse: closeCreatePanel }] = useBoolean(false);
  const [sharedServices, setSharedServices] = useState([] as Array<SharedService>);
  const apiCall = useAuthApiCall();

  useEffect(() => {
    const getSharedServices = async () => {
      const ss = (await apiCall(ApiEndpoint.SharedServices, HttpMethod.Get)).sharedServices;
      setSharedServices(ss);
    }
    getSharedServices();
  }, [apiCall]);

  const updateSharedService = (ss: SharedService) => {
    let ssList = [...sharedServices];
    let i = ssList.findIndex((f: SharedService) => f.id === ss.id);
    ssList.splice(i, 1, ss);
    setSharedServices(ssList);
  };

  const removeSharedService = (ss: SharedService) => {
    let ssList = [...sharedServices];
    let i = ssList.findIndex((f: SharedService) => f.id === ss.id);
    ssList.splice(i, 1);
    setSharedServices(ssList);
  };

  const addSharedService = (ss: SharedService) => {
    let ssList = [...sharedServices];
    ssList.push(ss);
    setSharedServices(ssList);
  }

  return (
    <>
      <Stack className="tre-panel">
        <Stack.Item>
          <Stack horizontal horizontalAlign="space-between">
            <h1>Shared Services</h1>
            <PrimaryButton iconProps={{ iconName: 'Add' }} text="Create new" onClick={createNew} />
            <CreateUpdateResource
              isOpen={createPanelOpen}
              onClose={closeCreatePanel}
              resourceType={ResourceType.SharedService}
              onAddResource={(r: Resource) => addSharedService(r as SharedService)}
            />
          </Stack>
        </Stack.Item>
        <Stack.Item>
          <ResourceCardList
            resources={sharedServices}
            updateResource={(r: Resource) => updateSharedService(r as SharedService)}
            removeResource={(r: Resource) => removeSharedService(r as SharedService)}
            emptyText="This TRE has no shared services." />
        </Stack.Item>
      </Stack>
    </>
  );
};

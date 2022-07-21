import React, { useContext, useEffect, useState } from 'react';
import { Resource } from '../../models/resource';
import { ResourceCardList } from '../shared/ResourceCardList';
import { PrimaryButton, Stack } from '@fluentui/react';
import { ResourceType } from '../../models/resourceType';
import { SharedService } from '../../models/sharedService';
import { HttpMethod, useAuthApiCall } from '../../hooks/useAuthApiCall';
import { ApiEndpoint } from '../../models/apiEndpoints';
import { CreateUpdateResourceContext } from '../../contexts/CreateUpdateResourceContext';
import { RoleName } from '../../models/roleNames';
import { SecuredByRole } from './SecuredByRole';

interface SharedServiceProps{
  readonly?: boolean
}

export const SharedServices: React.FunctionComponent<SharedServiceProps> = (props: SharedServiceProps) => {
  const createFormCtx = useContext(CreateUpdateResourceContext);
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
            {
              !props.readonly &&
              <SecuredByRole allowedRoles={[RoleName.TREAdmin]} workspaceAuth={false} element={
                <PrimaryButton iconProps={{ iconName: 'Add' }} text="Create new" onClick={() => {
                  createFormCtx.openCreateForm({
                    resourceType: ResourceType.SharedService,
                    onAdd: (r: Resource) => addSharedService(r as SharedService)
                  })
                }} />
              } />
            }
          </Stack>
        </Stack.Item>
        <Stack.Item>
          <ResourceCardList
            resources={sharedServices}
            updateResource={(r: Resource) => updateSharedService(r as SharedService)}
            removeResource={(r: Resource) => removeSharedService(r as SharedService)}
            emptyText="This TRE has no shared services."
            readonly={props.readonly} />
        </Stack.Item>
      </Stack>
    </>
  );
};

import time
import os
import uuid
import logging
from typing import List

from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.identity import DefaultAzureCredential
from azure.mgmt.containerinstance.models import (ContainerGroup,
                                                 Container,
                                                 ContainerGroupRestartPolicy,
                                                 ContainerGroupNetworkProfile,
                                                 EnvironmentVariable,
                                                 ImageRegistryCredential,
                                                 ContainerGroupIdentity,
                                                 ResourceRequests,
                                                 ResourceRequirements,
                                                 OperatingSystemTypes)
from azure.mgmt.network import NetworkManagementClient

from shared.azure_identity_credential_adapter import AzureIdentityCredentialAdapter


class CNABBuilder:
    def __init__(self, resource_request_message: dict):
        self._resource_group_name = os.environ["RESOURCE_GROUP_NAME"]
        self._subscription_id = os.environ["CNAB_AZURE_SUBSCRIPTION_ID"]
        self._message = resource_request_message
        self._container_group_name = ""
        self._location = ""

    def _build_porter_cmd_line(self) -> List[str]:
        porter_parameters = ""
        for key in self._message['parameters']:
            porter_parameters += " --param " + key + "=" + self._message['parameters'][key]

        installation_id = self._message['parameters']['tre_id'] + "-" + self._message['parameters']['workspace_id']
        start_command_line = ["/bin/bash", "-c", "porter "
                              + self._message['action'] + " "
                              + installation_id
                              + " --reference "
                              + os.environ["REGISTRY_SERVER"]
                              + os.environ["WORKSPACES_PATH"]
                              + self._message['name'] + ":"
                              + "v" + self._message['version'] + " "
                              + porter_parameters
                              + " -d azure && porter show " + installation_id]

        # start_command_line = ["/bin/bash", "-c", "sleep 600000000"]
        return start_command_line

    def _build_cnab_env_variables(self) -> List[str]:
        env_variables = []
        for key, value in os.environ.items():
            if key.startswith("CNAB_AZURE"):
                env_variables.append(EnvironmentVariable(name=key, value=value))

        env_variables.append(EnvironmentVariable(name="CNAB_AZURE_RESOURCE_GROUP", value=self._resource_group_name))
        env_variables.append(EnvironmentVariable(name="CNAB_AZURE_LOCATION", value=self._location))

        return env_variables

    def _get_network_profile(self) -> ContainerGroupNetworkProfile:
        default_credential = DefaultAzureCredential()

        network_client = NetworkManagementClient(default_credential, self._subscription_id)

        net_results = network_client.network_profiles.list(resource_group_name=self._resource_group_name)

        if net_results:
            net_result = net_results.next()
        else:
            raise Exception("No network profile")

        network_profile = ContainerGroupNetworkProfile(id=net_result.id)
        return network_profile

    def _setup_aci_deployment(self) -> ContainerGroup:

        self._location = self._message['parameters']['location']
        self._container_group_name = "aci-cnab-" + str(uuid.uuid4())
        container_image_name = os.environ['CNAB_IMAGE']

        image_registry_credentials = [ImageRegistryCredential(server=os.environ["REGISTRY_SERVER"],
                                                              username=os.environ["CNAB_AZURE_REGISTRY_USERNAME"],
                                                              password=os.environ["CNAB_AZURE_REGISTRY_PASSWORD"])]

        managed_identity = ContainerGroupIdentity(type='UserAssigned',
                                                  user_assigned_identities={
                                                      os.environ["CNAB_AZURE_USER_MSI_RESOURCE_ID"]: {}})

        container_resource_requests = ResourceRequests(memory_in_gb=1, cpu=1.0)
        container_resource_requirements = ResourceRequirements(requests=container_resource_requests)

        container = Container(name=self._container_group_name,
                              image=container_image_name,
                              resources=container_resource_requirements,
                              command=self._build_porter_cmd_line(),
                              environment_variables=self._build_cnab_env_variables())

        group = ContainerGroup(location=self._location,
                               containers=[container],
                               image_registry_credentials=image_registry_credentials,
                               os_type=OperatingSystemTypes.linux,
                               network_profile=self._get_network_profile(),
                               restart_policy=ContainerGroupRestartPolicy.never,
                               identity=managed_identity)
        return group

    def deploy_aci(self):
        group = self._setup_aci_deployment()

        credential = AzureIdentityCredentialAdapter()
        aci_client = ContainerInstanceManagementClient(credential, self._subscription_id)
        result = aci_client.container_groups.create_or_update(self._resource_group_name, self._container_group_name,
                                                              group)

        while result.done() is False:
            logging.info('-- Deploying -- ' + self._container_group_name + " to " + self._resource_group_name)
            time.sleep(1)

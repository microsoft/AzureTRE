import time
import os

import logging
from typing import List

from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.containerinstance.models import (ContainerGroup,
                                                 Container,
                                                 ContainerGroupRestartPolicy,
                                                 EnvironmentVariable,
                                                 ImageRegistryCredential,
                                                 ContainerGroupIdentity,
                                                 ResourceRequests,
                                                 ResourceRequirements,
                                                 OperatingSystemTypes)

from shared.azure_identity_credential_adapter import AzureIdentityCredentialAdapter
from shared.service_bus import ServiceBus
from resources import strings


class CNABBuilder:
    def __init__(self, resource_request_message: dict):
        self._resource_group_name = os.environ["RESOURCE_GROUP_NAME"]
        self._subscription_id = os.environ["CNAB_AZURE_SUBSCRIPTION_ID"]
        self._message = resource_request_message
        self._container_group_name = ""
        self._location = ""
        self._id = ""

    def _build_porter_command(self) -> List[str]:
        porter_parameters = ""
        for key in self._message['parameters']:
            porter_parameters += " --param " + key + "=" + self._message['parameters'][key]

        for key, value in os.environ.items():
            if key.startswith("param_"):
                porter_parameters += " --param " + key.replace('param_', '') + "=" + value

        installation_id = self._message['parameters']['tre_id'] + "-" + self._message['parameters']['workspace_id']
        command_line = ["/bin/bash", "-c", "az login --identity "
                        + "&& TOKEN=$(az acr login --name msfttreacr --expose-token --output tsv --query accessToken) "
                        + "&& docker login msfttreacr.azurecr.io --username 00000000-0000-0000-0000-000000000000 --password $TOKEN "
                        + "&& porter "
                        + self._message['action'] + " "
                        + installation_id
                        + " --reference "
                        + os.environ["REGISTRY_SERVER"]
                        + os.environ["WORKSPACES_PATH"]
                        + self._message['name'] + ":"
                        + "v" + self._message['version'] + " "
                        + porter_parameters
                        + " --cred ./home/porter/azure.json"
                        + " --driver azure && porter show " + installation_id]

        return command_line

    @staticmethod
    def _get_environment_variable(key, value):
        if key.startswith("CNAB_AZURE"):
            return EnvironmentVariable(name=key, value=value)
        if key.startswith("SEC_"):
            return EnvironmentVariable(name=key.replace("SEC_", ""), secure_value=value)

    def _build_cnab_env_variables(self) -> List[EnvironmentVariable]:
        env_variables = [self._get_environment_variable(key, value) for key, value in os.environ.items()
                         if key.startswith("CNAB_AZURE") or key.startswith("SEC_")]

        env_variables.append(EnvironmentVariable(name="CNAB_AZURE_RESOURCE_GROUP", value=self._resource_group_name))
        env_variables.append(EnvironmentVariable(name="CNAB_AZURE_LOCATION", value=self._location))

        return env_variables

    def _setup_aci_deployment(self) -> ContainerGroup:
        """
        Prepares a Container Group and a Container for deployment to ACI
        :return: The prepared container group
        """

        self._location = self._message['parameters']['azure_location']
        self._id = self._message['id']
        self._container_group_name = "aci-cnab-" + self._id
        container_image_name = os.environ['CNAB_IMAGE']

        image_registry_credentials = [ImageRegistryCredential(server=os.environ["REGISTRY_SERVER"],
                                                              username=os.environ["SEC_CNAB_AZURE_REGISTRY_USERNAME"],
                                                              password=os.environ["SEC_CNAB_AZURE_REGISTRY_PASSWORD"])]

        managed_identity = ContainerGroupIdentity(type='UserAssigned',
                                                  user_assigned_identities={os.environ["CNAB_AZURE_USER_MSI_RESOURCE_ID"]: {}})

        container_resource_requests = ResourceRequests(memory_in_gb=1, cpu=1.0)
        container_resource_requirements = ResourceRequirements(requests=container_resource_requests)

        container = Container(name=self._container_group_name,
                              image=container_image_name,
                              resources=container_resource_requirements,
                              command=self._build_porter_command(),
                              environment_variables=self._build_cnab_env_variables())

        group = ContainerGroup(location=self._location,
                               containers=[container],
                               image_registry_credentials=image_registry_credentials,
                               os_type=OperatingSystemTypes.linux,
                               restart_policy=ContainerGroupRestartPolicy.never,
                               identity=managed_identity)

        return group

    def _aci_run_completed(self, aci_client, service_bus) -> bool:
        logs = aci_client.containers.list_logs(self._resource_group_name, self._container_group_name, self._container_group_name)
        if "Error" in logs.content:
            service_bus.send_status_update_message(self._id, strings.RESOURCE_STATUS_DEPLOYMENT_FAILED, logs.content)
            logging.error(logs.content.split("Error", 1)[1])
            return True
        elif "Success" in logs.content:
            service_bus.send_status_update_message(self._id, strings.RESOURCE_STATUS_DEPLOYED, logs.content)
            logging.info(logs.content.split("Success", 1)[1])
            return True
        else:
            service_bus.send_status_update_message(self._id, strings.RESOURCE_STATUS_DEPLOYING, strings.WAITING_FOR_RUNNER)
            logging.info(strings.WAITING_FOR_RUNNER)
            return False

    def deploy_aci(self):
        """
        Deploys a CNAB container into ACI with parameters to run porter
        """

        group = self._setup_aci_deployment()

        credential = AzureIdentityCredentialAdapter()
        aci_client = ContainerInstanceManagementClient(credential, self._subscription_id)

        service_bus = ServiceBus()
        service_bus.send_status_update_message(self._id, strings.RESOURCE_STATUS_DEPLOYING, "Deploying ACI container: " + self._container_group_name)

        result = aci_client.container_groups.create_or_update(self._resource_group_name, self._container_group_name,
                                                              group)

        while not result.done():
            logging.info(strings.RESOURCE_STATUS_DEPLOYING + self._container_group_name + " to " + self._resource_group_name)
            time.sleep(1)

        service_bus.send_status_update_message(self._id, strings.RESOURCE_STATUS_DEPLOYING, "ACI container deployed " + self._container_group_name)

        while not self._aci_run_completed(aci_client, service_bus):
            time.sleep(10)

        logging.info(strings.MESSAGE_PROCESSED)

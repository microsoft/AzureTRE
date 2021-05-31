import json
import sys
import time
import os
import uuid
import logging

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

resource_group_name = os.environ["RESOURCE_GROUP_NAME"]
subscription_id = os.environ["CNAB_AZURE_SUBSCRIPTION_ID"]
container_group_name = ""
location = ""
message = ""

def build_porter_cmd_line(message):
    porter_parameters = ""
    for key in message['parameters']:
        porter_parameters += " --param " + key + "=" + message['parameters'][key]

    start_command_line = "/bin/bash -c 'az login && porter " + message['operation'] + " CNAB --tag " + message[
        'bundle-name'] + porter_parameters + " -d azure && porter show test'"

    return start_command_line


def build_cnab_env_variables():
    env_variables = []
    for key, value in os.environ.items():
        if key.startswith("CNAB_AZURE"):
            env_variables.append(EnvironmentVariable(name=key, value=value))

    env_variables.append(EnvironmentVariable(name="CNAB_AZURE_RESOURCE_GROUP", value=resource_group_name))
    env_variables.append(EnvironmentVariable(name="CNAB_AZURE_LOCATION", value=location))

    return env_variables


def get_network_profile():
    default_credential = DefaultAzureCredential()

    network_client = NetworkManagementClient(default_credential, subscription_id)

    net_results = network_client.network_profiles.list(resource_group_name=resource_group_name)

    if net_results:
        net_result = net_results.next()
    else:
        print('No network profile found')

    network_profile = ContainerGroupNetworkProfile(id=net_result.id)
    return network_profile


def setup_aci_deployment():
    global location
    global container_group_name
    
    location = message['parameters']['location']
    container_group_name = "aci-cnab-" + str(uuid.uuid4())
    container_image_name = message['CNAB-image']

    image_registry_credentials = [ImageRegistryCredential(server=os.environ["REGISTRY_SERVER"],
                                                          username=os.environ["REGISTRY_USER_NAME"],
                                                          password=os.environ["REGISTRY_USER_PASSWORD"])]

    managed_identity = ContainerGroupIdentity(type='UserAssigned',
                                              user_assigned_identities={
                                                  os.environ["CNAB_AZURE_USER_MSI_RESOURCE_ID"]: {}})

    container_resource_requests = ResourceRequests(memory_in_gb=1, cpu=1.0)
    container_resource_requirements = ResourceRequirements(requests=container_resource_requests)

    container = Container(name=container_group_name,
                          image=container_image_name,
                          resources=container_resource_requirements,
                          command=build_porter_cmd_line(message).split(),
                          environment_variables=build_cnab_env_variables())

    group = ContainerGroup(location=location,
                           containers=[container],
                           image_registry_credentials=image_registry_credentials,
                           os_type=OperatingSystemTypes.linux,
                           network_profile=get_network_profile(),
                           restart_policy=ContainerGroupRestartPolicy.never,
                           identity=managed_identity)
    return group


def deploy_aci():
    group = setup_aci_deployment()
    
    credential = AzureIdentityCredentialAdapter()
    aci_client = ContainerInstanceManagementClient(credential,
                                                   subscription_id)
    result = aci_client.container_groups.create_or_update(resource_group_name,
                                                          container_group_name,
                                                          group)

    while result.done() is False:
        logging.info('-- Deploying -- ' + container_group_name + " to " + resource_group_name)
        time.sleep(1)

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


RESOURCE_GROUP_NAME = os.environ["RESOURCE_GROUP_NAME"]
SUBSCRIPTION_ID = os.environ["CNAB_AZURE_SUBSCRIPTION_ID"]
CONTAINER_GROUP_NAME = ""
LOCATION = ""
MESSAGE = ""


def build_porter_cmd_line() -> str:
    porter_parameters = ""
    for key in MESSAGE['parameters']:
        porter_parameters += " --param " + key + "=" + MESSAGE['parameters'][key]

    start_command_line = "/bin/bash -c porter " + MESSAGE['operation'] + " CNAB --tag " + MESSAGE[
        'bundle-name'] + porter_parameters + " -d azure && porter show CNAB"

    logging.info("Creating a runner with:" + start_command_line)
    return start_command_line


def build_cnab_env_variables() -> str:
    env_variables = []
    for key, value in os.environ.items():
        if key.startswith("CNAB_AZURE"):
            env_variables.append(EnvironmentVariable(name=key, value=value))

    env_variables.append(EnvironmentVariable(name="CNAB_AZURE_RESOURCE_GROUP", value=RESOURCE_GROUP_NAME))
    env_variables.append(EnvironmentVariable(name="CNAB_AZURE_LOCATION", value=LOCATION))

    return env_variables


def get_network_profile() -> ContainerGroupNetworkProfile:
    default_credential = DefaultAzureCredential()

    network_client = NetworkManagementClient(default_credential, SUBSCRIPTION_ID)

    net_results = network_client.network_profiles.list(resource_group_name=RESOURCE_GROUP_NAME)

    if net_results:
        net_result = net_results.next()
    else:
        logging.info('No network profile found')

    network_profile = ContainerGroupNetworkProfile(id=net_result.id)
    return network_profile


def setup_aci_deployment() -> ContainerGroup:
    global LOCATION
    global CONTAINER_GROUP_NAME
    
    LOCATION = MESSAGE['parameters']['location']
    CONTAINER_GROUP_NAME = "aci-cnab-" + str(uuid.uuid4())
    container_image_name = MESSAGE['CNAB-image']

    image_registry_credentials = [ImageRegistryCredential(server=os.environ["REGISTRY_SERVER"],
                                                          username=os.environ["REGISTRY_USER_NAME"],
                                                          password=os.environ["REGISTRY_USER_PASSWORD"])]

    managed_identity = ContainerGroupIdentity(type='UserAssigned',
                                              user_assigned_identities={
                                                  os.environ["CNAB_AZURE_USER_MSI_RESOURCE_ID"]: {}})

    container_resource_requests = ResourceRequests(memory_in_gb=1, cpu=1.0)
    container_resource_requirements = ResourceRequirements(requests=container_resource_requests)

    container = Container(name=CONTAINER_GROUP_NAME,
                          image=container_image_name,
                          resources=container_resource_requirements,
                          command=build_porter_cmd_line().split(),
                          environment_variables=build_cnab_env_variables())

    group = ContainerGroup(location=LOCATION,
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
    aci_client = ContainerInstanceManagementClient(credential, SUBSCRIPTION_ID)
    result = aci_client.container_groups.create_or_update(RESOURCE_GROUP_NAME, CONTAINER_GROUP_NAME, group)

    while result.done() is False:
        logging.info('-- Deploying -- ' + CONTAINER_GROUP_NAME + " to " + RESOURCE_GROUP_NAME)
        time.sleep(1)

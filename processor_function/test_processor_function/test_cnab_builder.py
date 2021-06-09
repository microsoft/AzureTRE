import os
from mock import patch

from azure.mgmt.containerinstance.models import EnvironmentVariable

from shared.cnab_builder import CNABBuilder


@patch.dict(os.environ, {"CNAB_AZURE_MSI_TYPE": "msi-type",
                         "CNAB_AZURE_SUBSCRIPTION_ID": "sub-id",
                         "SEC_ARM_CLIENT_ID": "some-key",
                         "CNAB_IMAGE": "some value",
                         "SOMETHING_ELSE": "whatever",
                         "RESOURCE_GROUP_NAME": "rg-name"})
def test_build_cnab_env_variables_builds_the_correct_variables():
    builder = CNABBuilder({})

    actual_env_variables = builder._build_cnab_env_variables()
    assert len(actual_env_variables) == 5
    assert EnvironmentVariable(name="CNAB_AZURE_MSI_TYPE", value="msi-type") in actual_env_variables
    assert EnvironmentVariable(name="CNAB_AZURE_SUBSCRIPTION_ID", value="sub-id") in actual_env_variables
    assert EnvironmentVariable(name="ARM_CLIENT_ID", secure_value="some-key") in actual_env_variables
    assert EnvironmentVariable(name="CNAB_AZURE_RESOURCE_GROUP", value="rg-name") in actual_env_variables
    assert EnvironmentVariable(name="CNAB_AZURE_LOCATION", value="") in actual_env_variables

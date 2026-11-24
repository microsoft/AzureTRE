import os

import pytest

from shared.config import get_config

REQUIRED = {
    "REGISTRY_SERVER": "acr",
    "TERRAFORM_STATE_CONTAINER_NAME": "tfstate",
    "MGMT_RESOURCE_GROUP_NAME": "rg-mgmt",
    "MGMT_STORAGE_ACCOUNT_NAME": "stmgmt",
    "SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE": "status",
    "SERVICE_BUS_RESOURCE_REQUEST_QUEUE": "requests",
    "SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE": "sb",
    "AZURE_SUBSCRIPTION_ID": "sub",
    "ARM_CLIENT_ID": "client",
    "AZURE_TENANT_ID": "tenant",
    "ARM_USE_MSI": "true",
}


@pytest.fixture
def environment(monkeypatch):
    for name in list(os.environ):
        if name.startswith("RP_BUNDLE") or name in ("AZURE_ENVIRONMENT", "DEVCONTAINER"):
            monkeypatch.delenv(name)
    for name, value in REQUIRED.items():
        monkeypatch.setenv(name, value)
    return monkeypatch


@pytest.mark.parametrize(
    "cloud, url",
    [
        (None, "https://stmgmt.blob.core.windows.net"),
        ("AzureUSGovernment", "https://stmgmt.blob.core.usgovcloudapi.net"),
        ("AzureChinaCloud", "https://stmgmt.blob.core.chinacloudapi.cn"),
    ],
)
def test_the_execution_leases_use_the_terraform_state_account(environment, cloud, url):
    if cloud:
        environment.setenv("AZURE_ENVIRONMENT", cloud)
    assert get_config()["mgmt_blob_url"] == url


@pytest.mark.parametrize("value, expected", [(None, False), ("false", False), ("true", True), ("True", True)])
def test_the_session_lock_test_setting_is_off_by_default(environment, value, expected):
    if value is not None:
        environment.setenv("RP_BUNDLE_test_skip_session_lock_renewal", value)
    assert get_config()["test_skip_session_lock_renewal"] is expected

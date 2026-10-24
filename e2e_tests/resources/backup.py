"""Back up and restore the shared file share of a test-created workspace through Azure Resource Manager."""

import asyncio
from datetime import datetime, timedelta, timezone
import logging

from e2e_tests.resources.sql_probe import ARM

BACKUP_API = "2023-04-01"
GROUP_API = "2021-04-01"
LOCK_API = "2020-05-01"
STORAGE_API = "2023-05-01"
SOFT_DELETE_DAYS = 14
FILE_DATA_PRIVILEGED_CONTRIBUTOR = "69566ab7-960f-475b-8e7c-b3118f30c6bd"
SHARE = "vm-shared-storage"
FINISHED_JOB_STATES = {"Completed", "CompletedWithWarnings", "Failed", "Cancelled"}
LOGGER = logging.getLogger(__name__)


def names(workspace_id, tre_id):
    short_id = workspace_id[-4:]
    return {
        "group": f"rg-{tre_id}-ws-{short_id}",
        "vault": f"arsv-{tre_id}-ws-{short_id}",
        "account": f"stgws{short_id}",
    }


async def start_job(arm, path, body):
    """POST a backup or restore request and return the ID of the job that Azure Backup starts for it."""
    token = await asyncio.to_thread(arm.credential.get_token, f"{ARM}/.default")
    headers = {"Authorization": f"Bearer {token.token}"}
    response = await arm.client.post(f"{ARM}{path}", params={"api-version": BACKUP_API}, headers=headers, json=body)
    if response.status_code != 202:
        raise RuntimeError(f"ARM POST {path} failed with HTTP {response.status_code}")
    status_url = response.headers.get("Azure-AsyncOperation") or response.headers["Location"]
    async with asyncio.timeout(10 * 60):
        while True:
            await asyncio.sleep(10)
            token = await asyncio.to_thread(arm.credential.get_token, f"{ARM}/.default")
            status = await arm.client.get(status_url, headers={"Authorization": f"Bearer {token.token}"})
            if status.status_code == 202:
                continue
            if status.status_code != 200:
                raise RuntimeError(f"Backup operation status failed with HTTP {status.status_code}")
            result = status.json()
            if result.get("status") == "InProgress":
                continue
            job_id = result.get("properties", {}).get("jobId")
            if result.get("status") != "Succeeded" or not job_id:
                raise AssertionError(f"Azure Backup did not start a job: status={result.get('status')}")
            return job_id


async def wait_for_job(arm, vault_id, job_id, minutes=45):
    async with asyncio.timeout(minutes * 60):
        while True:
            job = await arm.request("GET", f"{vault_id}/backupJobs/{job_id}", BACKUP_API)
            state = job.get("properties", {}).get("status")
            if state in FINISHED_JOB_STATES:
                if state != "Completed":
                    raise AssertionError(f"Azure Backup job {job_id} ended as {state}")
                return job
            await asyncio.sleep(30)


def arm_id(resource_id):
    """Azure Backup returns IDs that start with /Subscriptions/. The ARM client accepts /subscriptions/ only."""
    prefix = "/subscriptions/"
    return prefix + resource_id[len(prefix) :] if resource_id.lower().startswith(prefix) else resource_id


async def file_share_items(arm, vault_id):
    items = await arm.request(
        "GET",
        f"{vault_id}/backupProtectedItems",
        BACKUP_API,
        query={"$filter": "backupManagementType eq 'AzureStorage'"},
    )
    return [{**item, "id": arm_id(item["id"])} for item in items.get("value", [])]


async def protected_share(arm, vault_id):
    shares = [item for item in await file_share_items(arm, vault_id) if item["properties"].get("friendlyName") == SHARE]
    if len(shares) != 1:
        raise AssertionError(f"Expected one protected file share in the vault, found {len(shares)}")
    return shares[0]


async def back_up_now(arm, vault_id, item_id):
    expiry = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = {"properties": {"objectType": "AzureFileShareBackupRequest", "recoveryPointExpiryTimeInUTC": expiry}}
    await wait_for_job(arm, vault_id, await start_job(arm, f"{item_id}/backup", body))


async def recovery_points(arm, item_id):
    points = (await arm.request("GET", f"{item_id}/recoveryPoints", BACKUP_API)).get("value", [])
    return sorted(points, key=lambda point: point["properties"].get("recoveryPointTime", ""))


async def restore_file(arm, vault_id, item_id, point_name, account_id, path):
    body = {
        "properties": {
            "objectType": "AzureFileShareRestoreRequest",
            "recoveryType": "OriginalLocation",
            "sourceResourceId": account_id,
            "copyOptions": "Overwrite",
            "restoreRequestType": "ItemLevelRestore",
            "restoreFilePaths": [{"path": path, "fileSpecType": "File"}],
        }
    }
    job_id = await start_job(arm, f"{item_id}/recoveryPoints/{point_name}/restore", body)
    await wait_for_job(arm, vault_id, job_id)


async def wait_until_gone(arm, resource_id, api_version, minutes):
    async with asyncio.timeout(minutes * 60):
        while await arm.request("GET", resource_id, api_version, missing_ok=True) is not None:
            await asyncio.sleep(30)


async def soft_delete_turned_off(arm, vault_id):
    """Try to turn off soft delete. Azure refuses this for some vaults, for example with enhanced security on."""
    config_id = f"{vault_id}/backupconfig/vaultconfig"
    try:
        await arm.request("PATCH", config_id, BACKUP_API, body={"properties": {"softDeleteFeatureState": "Disabled"}})
    except RuntimeError:
        LOGGER.warning("Azure did not turn off soft delete in vault %s", vault_id)
    config = await arm.request("GET", config_id, BACKUP_API)
    return config["properties"]["softDeleteFeatureState"] == "Disabled"


async def remove_retained_backup(arm, group_id, vault_id, account_id):
    """Delete the vault and the resource group that a retained-backup uninstall keeps on purpose."""
    if await arm.request("GET", group_id, GROUP_API, missing_ok=True) is None:
        return
    vault_kept = False
    if await arm.request("GET", vault_id, BACKUP_API, missing_ok=True) is not None:
        # With soft delete on, Azure keeps the deleted data for 14 days, and the vault cannot be deleted.
        vault_kept = not await soft_delete_turned_off(arm, vault_id)
        for item in await file_share_items(arm, vault_id):
            container = item["id"].split("/protectedItems/")[0]
            await arm.request("DELETE", item["id"], BACKUP_API, missing_ok=True)
            if not vault_kept:
                await wait_until_gone(arm, item["id"], BACKUP_API, 15)
                await arm.request("DELETE", container, BACKUP_API, missing_ok=True)
                await wait_until_gone(arm, container, BACKUP_API, 15)
        if not vault_kept:
            await arm.request("DELETE", vault_id, BACKUP_API, missing_ok=True)
            await wait_until_gone(arm, vault_id, BACKUP_API, 15)
    # Azure Backup can leave its delete lock on the retained storage account.
    locks = await arm.request("GET", f"{group_id}/providers/Microsoft.Authorization/locks", LOCK_API)
    for lock in locks.get("value", []):
        await arm.request("DELETE", lock["id"], LOCK_API, missing_ok=True)
    if vault_kept:
        await arm.request("DELETE", account_id, STORAGE_API, missing_ok=True)
        delete_after = (datetime.now(timezone.utc) + timedelta(days=SOFT_DELETE_DAYS + 1)).date().isoformat()
        await arm.request(
            "PATCH",
            f"{group_id}/providers/Microsoft.Resources/tags/default",
            GROUP_API,
            body={"operation": "Merge", "properties": {"tags": {"e2e_delete_after": delete_after}}},
        )
        LOGGER.warning("Soft delete keeps vault %s. Delete %s after %s.", vault_id, group_id, delete_after)
        return
    await arm.request("DELETE", group_id, GROUP_API, missing_ok=True)
    await wait_until_gone(arm, group_id, GROUP_API, 30)

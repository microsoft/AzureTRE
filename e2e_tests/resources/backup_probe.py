"""Write and read a file on the workspace file share from a test-created workspace Windows VM."""

import asyncio
import json
from pathlib import Path
from uuid import uuid4

from e2e_tests.resources.sql_probe import COMPUTE_API, delete_after

SCRIPT = Path(__file__).with_name("backup_probe.ps1")
RESULT = "BACKUP_PROBE_RESULT="
FAILED = "BACKUP_PROBE_FAILED="


def expected_result(phase, probe_id):
    expected = {"phase": phase, "probe": probe_id, "private_dns": True}
    if phase == "access":
        return {**expected, "unassigned": 403}
    return {**expected, "matches": True}


def probe_result(resource, phase, probe_id):
    properties = resource.get("properties", {})
    view = properties.get("instanceView", {})
    state = view.get("executionState", "")
    lines = view.get("output", "").splitlines()
    if properties.get("provisioningState") in ("Failed", "Canceled") or state in ("Failed", "Canceled", "TimedOut"):
        stages = [line[len(FAILED) :] for line in lines if line.startswith(FAILED)]
        raise AssertionError(
            f"Backup probe failed: state={state}, exitCode={view.get('exitCode')}, stage={','.join(stages) or 'unknown'}"
        )
    if state != "Succeeded":
        return False
    if view.get("exitCode") != 0:
        raise AssertionError("Backup probe returned a non-zero exit code")
    results = [line[len(RESULT) :] for line in lines if line.startswith(RESULT)]
    if len(results) != 1:
        raise AssertionError("Backup probe returned no single result")
    actual = json.loads(results[0])
    if actual != expected_result(phase, probe_id):
        raise AssertionError(f"Backup probe result does not match: {actual}")
    return True


async def run_probe(arm, vm_id, location, *, account, share, probe_id, phase):
    parameters = {"Account": account, "Share": share, "ProbeId": probe_id, "Phase": phase}
    command = f"{vm_id}/runCommands/backup-probe-{uuid4().hex}"
    # Removing our command also terminates it if its deadline expired.
    async with delete_after(arm, command, COMPUTE_API):
        async with asyncio.timeout(20 * 60):
            await arm.request(
                "PUT",
                command,
                COMPUTE_API,
                body={
                    "location": location,
                    "properties": {
                        "source": {"script": SCRIPT.read_text()},
                        "parameters": [{"name": k, "value": v} for k, v in parameters.items()],
                        "timeoutInSeconds": 900,
                        "treatFailureAsDeploymentFailure": True,
                    },
                },
            )
            while True:
                result = await arm.request("GET", command, COMPUTE_API, expand=True)
                if probe_result(result, phase, probe_id):
                    return
                await asyncio.sleep(10)

"""Run a private Gitea probe from a test-created workspace Windows VM."""

import asyncio
import json
from pathlib import Path
from uuid import uuid4

from e2e_tests.resources.sql_probe import COMPUTE_API, delete_after

SCRIPT = Path(__file__).with_name("gitea_probe.ps1")
RESULT = "GITEA_PROBE_RESULT="
FAILED = "GITEA_PROBE_FAILED="


def expected_result(phase, probe_id):
    expected = {"phase": phase, "probe": probe_id, "private_dns": True, "content": True}
    if phase == "write":
        return {**expected, "anonymous_create": 401, "wrong_password": 401, "anonymous_read": 404}
    return {**expected, "deleted": True}


def probe_result(resource, phase, probe_id):
    properties = resource.get("properties", {})
    view = properties.get("instanceView", {})
    state = view.get("executionState", "")
    lines = view.get("output", "").splitlines()
    if properties.get("provisioningState") in ("Failed", "Canceled") or state in ("Failed", "Canceled", "TimedOut"):
        stages = [line[len(FAILED) :] for line in lines if line.startswith(FAILED)]
        raise AssertionError(
            f"Gitea probe failed: state={state}, exitCode={view.get('exitCode')}, stage={','.join(stages) or 'unknown'}"
        )
    if state != "Succeeded":
        return False
    if view.get("exitCode") != 0:
        raise AssertionError("Gitea probe returned a non-zero exit code")
    results = [line[len(RESULT) :] for line in lines if line.startswith(RESULT)]
    if len(results) != 1:
        raise AssertionError("Gitea probe returned no single result")
    actual = json.loads(results[0])
    if actual != expected_result(phase, probe_id):
        raise AssertionError(f"Gitea probe result does not match: {actual}")
    return True


async def run_probe(arm, vm_id, location, *, gitea_url, vault_name, secret_name, probe_id, phase):
    parameters = {
        "GiteaUrl": gitea_url,
        "VaultName": vault_name,
        "SecretName": secret_name,
        "ProbeId": probe_id,
        "Phase": phase,
    }
    command = f"{vm_id}/runCommands/gitea-probe-{uuid4().hex}"
    # Removing our command also terminates it if its deadline expired.
    async with delete_after(arm, command, COMPUTE_API):
        async with asyncio.timeout(45 * 60):
            await arm.request(
                "PUT",
                command,
                COMPUTE_API,
                body={
                    "location": location,
                    "properties": {
                        "source": {"script": SCRIPT.read_text()},
                        "parameters": [{"name": k, "value": v} for k, v in parameters.items()],
                        "timeoutInSeconds": 2400,
                        "treatFailureAsDeploymentFailure": True,
                    },
                },
            )
            while True:
                result = await arm.request("GET", command, COMPUTE_API, expand=True)
                if probe_result(result, phase, probe_id):
                    return
                await asyncio.sleep(10)

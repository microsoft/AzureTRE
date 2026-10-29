"""Run a private MySQL probe from a test-created workspace Linux VM."""

import asyncio
import json
from pathlib import Path
import re
from uuid import uuid4

from e2e_tests.resources.sql_probe import COMPUTE_API, delete_after

SCRIPT = Path(__file__).with_name("mysql_probe.sh")
RESULT = "MYSQL_PROBE_RESULT="
FAILED = "MYSQL_PROBE_FAILED="
PATTERNS = {
    "SERVER": r"[a-z0-9-]+\.mysql\.database\.azure\.com",
    "VAULT_NAME": r"[a-z0-9-]+",
    "SECRET_NAME": r"[a-z0-9-]+",
    "DATABASE": r"[a-z0-9_]+",
    "PROBE_ID": r"[a-f0-9]{32}",
    "PHASE": r"write|read",
}


def probe_script(**values):
    """Set the validated values in the script text. They contain no secrets."""
    if set(values) != set(PATTERNS):
        raise ValueError("Unexpected MySQL probe values")
    for name, value in values.items():
        if not re.fullmatch(PATTERNS[name], value):
            raise ValueError(f"Invalid MySQL probe value for {name}")
    header = "".join(f"{name}='{value}'\n" for name, value in values.items())
    shebang, body = SCRIPT.read_text().split("\n", 1)
    return f"{shebang}\n{header}{body}"


def probe_result(resource, phase, probe_id):
    properties = resource.get("properties", {})
    view = properties.get("instanceView", {})
    state = view.get("executionState", "")
    lines = view.get("output", "").splitlines()
    if properties.get("provisioningState") in ("Failed", "Canceled") or state in ("Failed", "Canceled", "TimedOut"):
        stages = [line[len(FAILED) :] for line in lines if line.startswith(FAILED)]
        raise AssertionError(
            f"MySQL probe failed: state={state}, exitCode={view.get('exitCode')}, stage={','.join(stages) or 'unknown'}"
        )
    if state != "Succeeded":
        return False
    if view.get("exitCode") != 0:
        raise AssertionError("MySQL probe returned a non-zero exit code")
    results = [line[len(RESULT) :] for line in lines if line.startswith(RESULT)]
    expected = {"phase": phase, "probe": probe_id, "row_count": 1, "private_dns": True}
    if len(results) != 1 or json.loads(results[0]) != expected:
        raise AssertionError("MySQL probe did not confirm the expected data and private DNS")
    return True


async def run_probe(arm, vm_id, location, *, server, vault_name, secret_name, database, probe_id, phase):
    script = probe_script(
        SERVER=server,
        VAULT_NAME=vault_name,
        SECRET_NAME=secret_name,
        DATABASE=database,
        PROBE_ID=probe_id,
        PHASE=phase,
    )
    command = f"{vm_id}/runCommands/mysql-probe-{uuid4().hex}"
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
                        "source": {"script": script},
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

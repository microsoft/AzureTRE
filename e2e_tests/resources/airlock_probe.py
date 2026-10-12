"""Transfer synthetic export data from a workspace VM and inspect its review copy."""

import asyncio
import base64
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from e2e_tests.resources.sql_probe import COMPUTE_API, delete_after


SCRIPT = Path(__file__).with_suffix(".ps1")
PROBE_TIMEOUT_SECONDS = 15 * 60
MARKER = "AIRLOCK_PROBE_RESULT="


def validate_parameters(vm_id, location, *, phase, probe_id, blob_name, content, container_url):
    """Reject path and command injection before creating a Run Command resource."""
    if not isinstance(vm_id, str) or not re.fullmatch(
        r"/subscriptions/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
        r"/resourceGroups/[a-zA-Z0-9_.()-]+"
        r"/providers/Microsoft\.Compute/virtualMachines/[a-zA-Z0-9-]+",
        vm_id,
        re.I,
    ):
        raise ValueError("Expected an Azure VM resource ID")
    if not isinstance(location, str) or not re.fullmatch(r"[a-z0-9]+", location):
        raise ValueError("Expected an Azure region name")
    if phase not in ("upload", "read"):
        raise ValueError("Expected an upload or read probe phase")
    if not isinstance(probe_id, str) or not re.fullmatch(r"[a-f0-9]{32}", probe_id):
        raise ValueError("Expected a 32-character probe ID")
    if not isinstance(blob_name, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}", blob_name):
        raise ValueError("Expected a safe, flat blob name")
    if blob_name.endswith(".") or blob_name.split(".", 1)[0].upper() in {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"{kind}{n}" for kind in ("COM", "LPT") for n in range(1, 10)),
    }:
        raise ValueError("Expected a valid Windows file name")
    if not isinstance(content, str):
        raise ValueError("Expected synthetic text content")
    encoded = content.encode("utf-8")
    if not 0 < len(encoded) <= 16384:
        raise ValueError("Expected 1 to 16384 bytes of synthetic text")
    if phase == "read":
        if container_url is not None:
            raise ValueError("A read probe must not receive a container URL")
    else:
        # Do not put the rejected URL in an exception: it contains a SAS token.
        try:
            parsed = urlsplit(container_url) if isinstance(container_url, str) else None
            valid = (
                parsed is not None
                and parsed.scheme == "https"
                and re.fullmatch(r"[a-z0-9]{3,24}\.blob\.core\.windows\.net", parsed.netloc)
                and re.fullmatch(r"/[a-z0-9](?:[a-z0-9-]{1,61})[a-z0-9]", parsed.path)
                and "--" not in parsed.path
                and parsed.fragment == ""
                and len(parse_qs(parsed.query).get("sig", [])) == 1
                and not any(char.isspace() for char in container_url)
            )
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("Expected an AzureCloud blob container SAS URL")
    return encoded


def _unique_object(items):
    if len({key for key, _ in items}) != len(items):
        raise ValueError("Duplicate evidence keys")
    return dict(items)


def probe_result(resource, *, phase, probe_id, expected_hash):
    """Accept only the exact successful evidence emitted by this probe."""
    properties = resource.get("properties", {})
    view = properties.get("instanceView", {})
    state = view.get("executionState", "")
    if properties.get("provisioningState") in ("Failed", "Canceled") or state in ("Failed", "Canceled", "TimedOut"):
        raise AssertionError("Airlock probe command failed")
    if state != "Succeeded":
        return False
    if type(view.get("exitCode")) is not int or view["exitCode"] != 0 or view.get("error"):
        raise AssertionError("Airlock probe did not exit successfully")
    output = view.get("output", "")
    lines = output.strip().splitlines() if isinstance(output, str) else []
    if len(lines) != 1 or not lines[0].startswith(MARKER):
        raise AssertionError("Airlock probe did not return exactly one result")
    try:
        evidence = json.loads(lines[0][len(MARKER) :], object_pairs_hook=_unique_object)
    except (ValueError, TypeError):
        raise AssertionError("Airlock probe returned invalid evidence") from None
    expected = {"phase": phase, "probe": probe_id, "sha256": expected_hash}
    if evidence != expected:
        raise AssertionError("Airlock probe data did not match the expected content")
    return True


async def run_probe(arm, vm_id, location, *, phase, probe_id, blob_name, content, container_url=None):
    encoded = validate_parameters(
        vm_id,
        location,
        phase=phase,
        probe_id=probe_id,
        blob_name=blob_name,
        content=content,
        container_url=container_url,
    )
    expected_hash = hashlib.sha256(encoded).hexdigest()
    parameters = {
        "Phase": phase,
        "ProbeId": probe_id,
        "BlobName": blob_name,
        "ContentBase64": base64.b64encode(encoded).decode("ascii"),
        "ExpectedSha256": expected_hash,
    }
    properties = {
        "source": {"script": SCRIPT.read_text()},
        "parameters": [{"name": name, "value": value} for name, value in parameters.items()],
        "timeoutInSeconds": 600,
        "treatFailureAsDeploymentFailure": True,
    }
    if container_url is not None:
        properties["protectedParameters"] = [{"name": "ContainerUrl", "value": container_url}]
    command = f"{vm_id}/runCommands/airlock-probe-{uuid4().hex}"
    # An accepted PUT can lose its response. Register cleanup before sending it.
    async with delete_after(arm, command, COMPUTE_API):
        async with asyncio.timeout(PROBE_TIMEOUT_SECONDS):
            await arm.request("PUT", command, COMPUTE_API, body={"location": location, "properties": properties})
            while True:
                resource = await arm.request("GET", command, COMPUTE_API, expand=True)
                if probe_result(resource, phase=phase, probe_id=probe_id, expected_hash=expected_hash):
                    return
                await asyncio.sleep(10)

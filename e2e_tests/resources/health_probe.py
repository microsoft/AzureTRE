"""Run a private FHIR probe from a test-created workspace Windows VM."""

import asyncio
from contextlib import asynccontextmanager
import json
import logging
from pathlib import Path
from uuid import uuid4

from e2e_tests.resources.sql_probe import COMPUTE_API, ROLE_API, delete_after

SCRIPT = Path(__file__).with_name("health_probe.ps1")
RESULT = "HEALTH_PROBE_RESULT="
FAILED = "HEALTH_PROBE_FAILED="
FHIR_DATA_CONTRIBUTOR = "5a1fc7df-4bf1-4951-a576-89034ee01acd"
DNS_ATTEMPTS = 3
DNS_RETRY_SECONDS = 60
LOGGER = logging.getLogger(__name__)


class ProbeFailure(AssertionError):
    def __init__(self, message, stages):
        super().__init__(message)
        self.stages = stages


def expected_result(phase, probe_id, dicom):
    expected = {"phase": phase, "probe": probe_id, "private_dns": True}
    if phase == "access":
        return {**expected, "fhir_version": "4.0.1", "anonymous": 401, "unassigned": 403}
    expected["count"] = 1
    if dicom:
        expected["dicom_anonymous"] = 401
    return expected


def probe_result(resource, phase, probe_id, dicom=False):
    properties = resource.get("properties", {})
    view = properties.get("instanceView", {})
    state = view.get("executionState", "")
    lines = view.get("output", "").splitlines()
    if properties.get("provisioningState") in ("Failed", "Canceled") or state in ("Failed", "Canceled", "TimedOut"):
        stages = [line[len(FAILED) :] for line in lines if line.startswith(FAILED)]
        raise ProbeFailure(
            f"Health probe failed: state={state}, exitCode={view.get('exitCode')}, stage={','.join(stages) or 'unknown'}",
            stages,
        )
    if state != "Succeeded":
        return False
    if view.get("exitCode") != 0:
        raise AssertionError("Health probe returned a non-zero exit code")
    results = [line[len(RESULT) :] for line in lines if line.startswith(RESULT)]
    if len(results) != 1:
        raise AssertionError("Health probe returned no single result")
    actual = json.loads(results[0])
    if actual != expected_result(phase, probe_id, dicom):
        raise AssertionError(f"Health probe result does not match: {actual}")
    return True


@asynccontextmanager
async def role_access(arm, scope, role, principal_id, subscription_id):
    """Grant only this VM a data role on one service, then remove the assignment."""
    assignment = f"{scope}/providers/Microsoft.Authorization/roleAssignments/{uuid4()}"
    body = {
        "properties": {
            "roleDefinitionId": f"/subscriptions/{subscription_id}/providers/Microsoft.Authorization/roleDefinitions/{role}",
            "principalId": principal_id,
            "principalType": "ServicePrincipal",
        }
    }
    # The PUT may have succeeded even if its response was lost.
    async with delete_after(arm, assignment, ROLE_API):
        await arm.request("PUT", assignment, ROLE_API, body=body)
        yield


async def run_probe(arm, vm_id, location, *, fhir_url, probe_id, phase, dicom_url=""):
    # A lookup of the FHIR name failed once on a new VM. The probe changes no data before this stage.
    for attempt in range(1, DNS_ATTEMPTS + 1):
        try:
            return await run_probe_once(
                arm, vm_id, location, fhir_url=fhir_url, probe_id=probe_id, phase=phase, dicom_url=dicom_url
            )
        except ProbeFailure as error:
            if error.stages != ["private-dns"] or attempt == DNS_ATTEMPTS:
                raise
            LOGGER.warning("Health probe %s failed at private-dns, attempt %d. Trying again.", phase, attempt)
            await asyncio.sleep(DNS_RETRY_SECONDS)


async def run_probe_once(arm, vm_id, location, *, fhir_url, probe_id, phase, dicom_url=""):
    parameters = {"FhirUrl": fhir_url, "ProbeId": probe_id, "Phase": phase}
    if dicom_url:
        parameters["DicomUrl"] = dicom_url
    command = f"{vm_id}/runCommands/health-probe-{uuid4().hex}"
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
                if probe_result(result, phase, probe_id, bool(dicom_url)):
                    return
                await asyncio.sleep(10)

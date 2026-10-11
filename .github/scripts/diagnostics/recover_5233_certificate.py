"""Retry only the disabled test certificate recorded in issue 5233."""

import json
import os
import time

from read_airlock_certificate import api

CERTIFICATE = "d9236f8f-7fbb-46d3-9c94-dea6daf32b7f"
FIREWALL = "7af8f146-d751-4587-a22e-eb44c1c6fbe2"
PATH = f"/shared-services/{CERTIFICATE}"
TERMINAL = {
    "deployed",
    "updated",
    "deleted",
    "action_succeeded",
    "deployment_failed",
    "updating_failed",
    "deleting_failed",
    "action_failed",
}
FAILED = {"deployment_failed", "updating_failed", "deleting_failed", "action_failed"}
SUCCESS = {"deployed", "updated", "deleted", "action_succeeded"}


def emit(**fields):
    print(json.dumps(fields), flush=True)


def get_operations(resource_id):
    code, result = api(f"/shared-services/{resource_id}/operations")
    assert code == 200
    return result["operations"]


def check_firewall():
    code, result = api(f"/shared-services/{FIREWALL}")
    assert code == 200
    firewall = result["sharedService"]
    assert firewall["id"] == FIREWALL and firewall["templateName"] == "tre-shared-service-firewall"
    assert firewall["deploymentStatus"] in {"deployed", "updated"}
    rules = firewall["properties"]["rule_collections"]
    assert all(rule["name"] != f"arc_svc_{CERTIFICATE}_rp_certs" for rule in rules)
    assert all(operation["status"] in TERMINAL for operation in get_operations(FIREWALL))
    emit(firewall=FIREWALL, status=firewall["deploymentStatus"], certificate_rule_absent=True)


def wait_for_deletion(operation_id):
    deadline = time.monotonic() + 3600
    main_complete_pipeline_visible = False
    while time.monotonic() < deadline:
        code, result = api(f"{PATH}/operations/{operation_id}")
        if code == 404:
            assert api(PATH)[0] == 404
            break
        assert code == 200
        operation = result["operation"]
        assert operation["resourceId"] == CERTIFICATE and operation["action"] == "uninstall"
        steps = operation["steps"]
        assert len(steps) == 2 and steps[0]["resourceId"] == CERTIFICATE and steps[1]["resourceId"] == FIREWALL
        emit(operation=operation_id, status=operation["status"], step_statuses=[step["status"] for step in steps])
        assert operation["status"] not in FAILED and all(step["status"] not in FAILED for step in steps)
        if steps[0]["status"] == "deleted" and steps[1]["status"] not in SUCCESS:
            assert operation["status"] == "pipeline_running"
            # This nested operation response itself proves that the resource
            # remained visible after its main step. Completion can race the GET.
            main_complete_pipeline_visible = True
            resource_code, resource = api(PATH)
            if resource_code == 404:
                break
            assert resource_code == 200 and resource["sharedService"]["deploymentStatus"] == "pipeline_running"
        if operation["status"] == "deleted":
            assert all(step["status"] in SUCCESS for step in steps)
        time.sleep(20)
    else:
        raise TimeoutError("Certificate cleanup did not finish within one hour")
    check_firewall()
    emit(
        certificate=CERTIFICATE,
        operation=operation_id,
        api_resource_absent=True,
        main_complete_pipeline_visible=main_complete_pipeline_visible,
        visibility_evidence="observed" if main_complete_pipeline_visible else "not_observed",
    )


def main():
    execute = os.environ["EXECUTE_RECOVERY"]
    assert execute in {"true", "false"}
    code, metadata = api("/.metadata")
    assert code == 200
    emit(api_version=metadata["api_version"], execute=execute == "true")
    if execute == "true":
        assert metadata["api_version"] == "0.28.4", "Deploy the reviewed API correction before recovery"
    code, resource = api(PATH)
    if code == 404:
        check_firewall()
        emit(certificate=CERTIFICATE, cleanup="already_absent")
        return
    assert code == 200
    certificate = resource["sharedService"]
    assert certificate["id"] == CERTIFICATE and certificate["templateName"] == "tre-shared-service-certs"
    assert certificate["templateVersion"] == "0.7.13" and certificate["isEnabled"] is False
    assert certificate["properties"]["description"] == "tre-shared-service-certs deployed via e2e tests"
    assert (
        certificate["properties"]["domain_prefix"] == "nexus" and certificate["properties"]["cert_name"] == "nexus-ssl"
    )
    code, services = api("/shared-services")
    assert code == 200
    assert not any(item["templateName"] == "tre-shared-service-sonatype-nexus" for item in services["sharedServices"])
    code, current_operations = api("/operations")
    assert code == 200
    assert all(operation["resourceId"] == CERTIFICATE for operation in current_operations["operations"])
    operations = get_operations(CERTIFICATE)
    active = [operation for operation in operations if operation["status"] not in TERMINAL]
    if active:
        assert len(active) == 1 and active[0]["resourceId"] == CERTIFICATE and active[0]["action"] == "uninstall"
        emit(existing_uninstall=active[0]["id"])
        if execute == "true":
            wait_for_deletion(active[0]["id"])
        return
    assert certificate["deploymentStatus"] == "deleting_failed"
    assert all(operation["status"] in TERMINAL for operation in get_operations(FIREWALL))
    emit(certificate=CERTIFICATE, status=certificate["deploymentStatus"], active_operations=0, nexus_absent=True)
    if execute == "false":
        return
    code, result = api(PATH, method="DELETE")
    assert code == 200
    operation = result["operation"]
    assert operation["resourceId"] == CERTIFICATE and operation["action"] == "uninstall"
    emit(certificate_uninstall_operation=operation["id"])
    wait_for_deletion(operation["id"])


if __name__ == "__main__":
    main()

import logging
import re
from datetime import datetime, timezone
import backoff
from httpx import TimeoutException
from e2e_tests.helpers import get_auth_header, get_full_endpoint
from e2e_tests.resources import strings

LOGGER = logging.getLogger(__name__)
_UUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
_OPERATION_PATH = re.compile(
    rf"/api/(?:workspaces/{_UUID}/(?:workspace-services/{_UUID}/(?:user-resources/{_UUID}/)?)?"
    rf"|shared-services/{_UUID}/)?operations/{_UUID}"
)
_CORRELATION_HEADERS = {
    "x-ms-request-id": _UUID,
    "x-ms-correlation-request-id": _UUID,
    "x-request-id": _UUID,
    "request-id": rf"(?:{_UUID}|\|[0-9a-f]{32}\.[0-9a-f]{16}\.)",
    "traceparent": r"00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}",
}


def polling_failure_details(response, operation_endpoint):
    """Return bounded metadata. Never copy bodies, URL parameters or arbitrary headers."""
    path = operation_endpoint.split("?", 1)[0].split("#", 1)[0]
    media_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    allowed_media_types = {"application/json", "application/problem+json", "text/plain", "text/html"}
    prefix = response.content[:64].lstrip().lower()
    if not response.content:
        body_kind = "empty"
    elif prefix.startswith((b"{", b"[")):
        body_kind = "json_like"
    elif prefix.startswith((b"<!doctype html", b"<html")):
        body_kind = "html_like"
    else:
        body_kind = "other"
    return {
        "utc_time": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "method": "GET",
        "path": path if _OPERATION_PATH.fullmatch(path) else "<redacted>",
        "status": response.status_code,
        "content_type": media_type if media_type in allowed_media_types else "other_or_missing",
        "body_bytes": len(response.content),
        "body_kind": body_kind,
        "correlation": {
            name: value
            for name, pattern in _CORRELATION_HEADERS.items()
            if (value := response.headers.get(name, "")) and re.fullmatch(pattern, value)
        },
    }


async def delete_done(client, operation_endpoint, access_token):
    delete_terminal_states = [strings.RESOURCE_STATUS_DELETED, strings.RESOURCE_STATUS_DELETING_FAILED]
    deployment_status, message, operation_steps = await check_deployment(client, operation_endpoint, access_token)
    return (
        (True, deployment_status, message, operation_steps)
        if deployment_status in delete_terminal_states
        else (False, deployment_status, message, operation_steps)
    )


async def install_done(client, operation_endpoint, access_token):
    install_terminal_states = [strings.RESOURCE_STATUS_DEPLOYED, strings.RESOURCE_STATUS_DEPLOYMENT_FAILED]
    deployment_status, message, operation_steps = await check_deployment(client, operation_endpoint, access_token)
    return (
        (True, deployment_status, message, operation_steps)
        if deployment_status in install_terminal_states
        else (False, deployment_status, message, operation_steps)
    )


async def patch_done(client, operation_endpoint, access_token):
    install_terminal_states = [strings.RESOURCE_STATUS_UPDATED, strings.RESOURCE_STATUS_UPDATING_FAILED]
    deployment_status, message, operation_steps = await check_deployment(client, operation_endpoint, access_token)
    return (
        (True, deployment_status, message, operation_steps)
        if deployment_status in install_terminal_states
        else (False, deployment_status, message, operation_steps)
    )


@backoff.on_exception(
    backoff.constant,
    TimeoutException,  # catching all timeout types (Connection, Read, etc.)
    max_time=90,
)
async def check_deployment(client, operation_endpoint, access_token):
    full_endpoint = get_full_endpoint(operation_endpoint)

    response = await client.get(full_endpoint, headers=get_auth_header(access_token), timeout=5.0)
    if response.status_code == 200:
        response_json = response.json()
        deployment_status = response_json["operation"]["status"]
        message = response_json["operation"]["message"]
        operation_steps = stringify_operation_steps(response_json["operation"]["steps"])
        return deployment_status, message, operation_steps
    elif response.status_code == 404:
        # 404 indicates the resource has been deleted (filtered out by get_by_id methods)
        # This is a valid state for deletion operations
        LOGGER.info(f"Resource not found (404) - treating as deleted: {operation_endpoint}")
        return strings.RESOURCE_STATUS_DELETED, "Resource has been deleted", ""
    else:
        LOGGER.error("Operation polling failed: %s", polling_failure_details(response, operation_endpoint))
        raise Exception("Non 200 response in check_deployment")


def stringify_operation_steps(steps):
    string = ""
    for i, step in enumerate(steps, 1):
        string += f"Step {i}: {step['stepTitle']}\n"
        string += f"{step['message']}\n\n"
    return string

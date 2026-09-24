"""Read-only Foundry image URL probes for the deployed E2E tests."""

import base64
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import datetime as dt
import hashlib
import json
import os
import re
import ssl
import struct
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zlib


DEFAULT_IMAGE = "https://raw.githubusercontent.com/microsoft/vscode/main/resources/linux/code.png"
API_VERSION = "2024-10-21"
ARM_VERSION = "2025-06-01"
MAX_BODY = 4 * 1024 * 1024
CASES = ("empty_inline", "unrelated_inline", "allowed_inline", "allowed_external",
         "unrelated_external", "empty_external")


@dataclass
class Reply:
    status: int
    body: dict

    @property
    def success(self):
        choices = self.body.get("choices", [])
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            return False
        message = choices[0].get("message")
        return (self.status == 200 and choices[0].get("finish_reason") == "stop"
                and isinstance(message, dict) and isinstance(message.get("content"), str)
                and bool(message["content"].strip()))

    @property
    def policy_denied(self):
        # A generic 400/403, invalid image, content filter or throttling is not enforcement.
        error = self.body.get("error")
        if self.status not in (400, 403) or not isinstance(error, dict):
            return False
        message = str(error.get("message", "")).lower()
        return "image url domain is not allowed in this environment" in message


def evaluate(probes):
    """Require healthy controls before accepting any negative result."""
    controls_ok = all(probes[name].success for name in CASES[:4])
    unrelated_ok = probes["unrelated_external"].policy_denied
    results = {}
    for name in CASES:
        reply = probes[name]
        if name in CASES[:4]:
            state = "pass" if reply.success else "blocked"
            reason = "image_processed" if reply.success else "positive_control_failed"
        elif reply.success:
            state, reason = "fail", "forbidden_image_processed"
        elif reply.policy_denied and controls_ok and unrelated_ok:
            state, reason = "pass", "explicit_domain_policy_rejection"
        else:
            state, reason = "blocked", "unverified_rejection_or_unhealthy_control"
        results[name] = {"state": state, "reason": reason, "http_status": reply.status}
    return results


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


def opener():
    certificate = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE")
    context = ssl.create_default_context(cafile=certificate)
    return urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=context))


def azure(arguments, subscription):
    command = ["az", *arguments, "--subscription", subscription, "--only-show-errors", "-o", "json"]
    completed = subprocess.run(command, text=True, capture_output=True, check=False, timeout=60)
    if completed.returncode:
        # CLI output can contain credentials. Do not copy it into pytest reports.
        raise RuntimeError(f"Azure CLI failed with exit code {completed.returncode}")
    return json.loads(completed.stdout)


def arm(resource_id, subscription):
    return azure(["rest", "--method", "get", "--url",
                  f"https://management.azure.com{resource_id}?api-version={ARM_VERSION}"], subscription)


def image_url(base, run_id, case):
    parts = urllib.parse.urlsplit(base)
    if (parts.scheme != "https" or not parts.hostname or parts.username or parts.password
            or parts.query or parts.fragment or parts.port not in (None, 443)):
        raise ValueError("Use a public HTTPS image URL without credentials, query parameters or redirects")
    return base + "?" + urllib.parse.urlencode({"run": run_id, "case": case})


def verify_config(config):
    base_image = config.get("image_url", DEFAULT_IMAGE)
    image_url(base_image, "validation", "validation")
    hostname = urllib.parse.urlsplit(base_image).hostname
    policies = {"empty": [], "unrelated": ["example.com"], "allowed": [hostname]}
    if set(config["accounts"]) != set(policies) or hostname == "example.com":
        raise ValueError("Supply distinct empty, unrelated and allowed policy controls")
    for field in ("subscription_id", "tenant_id"):
        uuid.UUID(config[field])
    for field in ("model_name", "model_version"):
        if not isinstance(config[field], str) or not config[field].strip():
            raise ValueError("Specify the same model name and version for all controls")
    identifiers = set()
    for account in config["accounts"].values():
        prefix = f'/subscriptions/{config["subscription_id"]}/resourceGroups/'
        pattern = re.escape(prefix) + r"[^/?#]+/providers/Microsoft.CognitiveServices/accounts/[a-zA-Z0-9-]+"
        if not re.fullmatch(pattern, account["id"], re.IGNORECASE):
            raise ValueError("Account is outside the selected subscription or has an invalid resource ID")
        if not re.fullmatch(r"[a-zA-Z0-9_.-]+", account["deployment"]):
            raise ValueError("Invalid deployment name")
        if account["id"].lower() in identifiers:
            raise ValueError("Each policy control requires a distinct account")
        identifiers.add(account["id"].lower())
    return policies


def verify_account(account, expected_id, fqdns, now=None):
    properties = account.get("properties", {})
    if (account.get("id", "").lower() != expected_id.lower() or account.get("kind") != "AIServices"
            or properties.get("provisioningState") != "Succeeded"
            or properties.get("restrictOutboundNetworkAccess") is not True
            or sorted(properties.get("allowedFqdnList") or []) != sorted(fqdns)):
        raise ValueError("ARM account readback does not match the required outbound policy")
    # ARM can omit an empty collection. That is the empty-list case under test.
    system = account.get("systemData", {})
    modified = system.get("lastModifiedAt") or system.get("createdAt")
    if not modified:
        raise ValueError("ARM did not return a policy modification timestamp")
    changed = dt.datetime.fromisoformat(modified.replace("Z", "+00:00"))
    now = now or dt.datetime.now(dt.timezone.utc)
    if changed.tzinfo is None or (now - changed).total_seconds() < 900:
        raise ValueError("Wait 15 minutes after the account's last modification before testing")


def verify_live(config):
    policies = verify_config(config)
    subscription = config["subscription_id"]
    context = azure(["account", "show"], subscription)
    if (context["id"].lower() != subscription.lower()
            or context["tenantId"].lower() != config["tenant_id"].lower()):
        raise ValueError("Azure context does not match the selected subscription and tenant")
    readbacks = {}
    for name, expected in config["accounts"].items():
        account = arm(expected["id"], subscription)
        verify_account(account, expected["id"], policies[name])
        model = arm(expected["id"] + "/deployments/" + expected["deployment"], subscription)
        properties = model["properties"]
        if (properties.get("provisioningState") != "Succeeded"
                or properties["model"].get("format") != "OpenAI"
                or properties["model"]["name"] != config["model_name"]
                or properties["model"]["version"] != config["model_version"]):
            raise ValueError("Deployed model does not match the selected model and version")
        subdomain = account["properties"]["customSubDomainName"]
        if not re.fullmatch(r"[a-zA-Z0-9-]+", subdomain):
            raise ValueError("Unexpected Foundry subdomain in ARM readback")
        readbacks[name] = {
            "endpoint": f"https://{subdomain}.openai.azure.com", "deployment": expected["deployment"],
            "account_properties": account["properties"], "system_data": account.get("systemData"),
            "model_properties": properties, "sku": model.get("sku"),
        }
    return readbacks


def inline_image():
    def chunk(kind, data):
        return struct.pack("!I", len(data)) + kind + data + struct.pack("!I", zlib.crc32(kind + data))
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack("!2I5B", 32, 32, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress((b"\x00" + b"\xff\x00\x00" * 32) * 32))
           + chunk(b"IEND", b""))
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def check_image(url):
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    with opener().open(request, timeout=30) as response:
        data = response.read(MAX_BODY + 1)
        if response.status != 200 or not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) > MAX_BODY:
            raise ValueError("The public control must return a PNG of at most 4 MiB without redirects")
        return hashlib.sha256(data).hexdigest()


def call_model(account, image, token, model_name):
    payload = {"messages": [{"role": "user", "content": [
        {"type": "text", "text": "<task>Describe this image briefly.</task>"},
        {"type": "image_url", "image_url": {"url": image, "detail": "low"}},
    ]}], "max_completion_tokens": 128}
    if model_name == "gpt-5.1":
        payload["reasoning_effort"] = "none"
    deployment = urllib.parse.quote(account["deployment"], safe="")
    url = f'{account["endpoint"]}/openai/deployments/{deployment}/chat/completions?api-version={API_VERSION}'
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={
        "Authorization": "Bearer " + token, "Content-Type": "application/json",
    })
    try:
        with opener().open(request, timeout=90) as response:
            body = json.loads(response.read(MAX_BODY))
            return Reply(response.status, body if isinstance(body, dict) else {})
    except urllib.error.HTTPError as error:
        try:
            body = json.loads(error.read(MAX_BODY))
        except (ValueError, UnicodeDecodeError):
            body = {}
        return Reply(error.code, body if isinstance(body, dict) else {})
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return Reply(0, {})


def run_probes(config):
    before = verify_live(config)
    base_image = config.get("image_url", DEFAULT_IMAGE)
    run_id = uuid.uuid4().hex
    image_hash = check_image(image_url(base_image, run_id, "operator-before"))
    token = azure(["account", "get-access-token", "--resource", "https://cognitiveservices.azure.com/"],
                  config["subscription_id"])["accessToken"]

    def account_probes(item):
        name, account = item
        return {name + "_inline": call_model(account, inline_image(), token, config["model_name"]),
                name + "_external": call_model(account, image_url(base_image, run_id, name), token, config["model_name"])}

    probes = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        for group in pool.map(account_probes, before.items()):
            probes.update(group)
    results = evaluate(probes)
    try:
        after = verify_live(config)
        if before != after or image_hash != check_image(image_url(base_image, run_id, "operator-after")):
            raise ValueError("Account, model or public image changed during the probes")
    except (RuntimeError, ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError):
        # Preserve unexpected acceptance even if later verification fails.
        for result in results.values():
            if result["state"] == "pass":
                result.update(state="blocked", reason="postflight_verification_failed")
    return results

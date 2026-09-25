"""Read-only policy probes using public Microsoft Learn MCP tools."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import json
import subprocess
import urllib.error
import urllib.request

from e2e_tests.resources import foundry


SERVER_URL = "https://learn.microsoft.com/api/mcp"
SERVER_HOST = "learn.microsoft.com"
DENY_ALL_FQDN = "deny-all.invalid"
POLICIES = {"empty": [], "unrelated": [DENY_ALL_FQDN], "allowed": ["raw.githubusercontent.com", SERVER_HOST]}
CASES = ("empty_text", "unrelated_text", "allowed_text", "allowed_metadata", "allowed_invoke",
         "unrelated_metadata", "unrelated_invoke", "empty_metadata", "empty_invoke")


@dataclass
class Reply:
    status: int
    body: dict

    def items(self, kind):
        output = self.body.get("output", [])
        if self.status != 200 or not isinstance(output, list):
            return []
        return [item for item in output if isinstance(item, dict) and item.get("type") == kind]

    @property
    def text_completed(self):
        return self.body.get("status") == "completed" and any(
            isinstance(part, dict) and isinstance(part.get("text"), str) and part["text"].strip()
            for item in self.items("message") if isinstance(item.get("content"), list)
            for part in item["content"])

    @property
    def metadata_imported(self):
        return any(not item.get("error") and isinstance(item.get("tools"), list) and item["tools"]
                   for item in self.items("mcp_list_tools"))

    @property
    def tool_completed(self):
        return any(item.get("status") == "completed" and not item.get("error")
                   and item.get("name") == "microsoft_docs_search" for item in self.items("mcp_call"))

    @property
    def policy_denied(self):
        error = self.body.get("error")
        return (self.status in (400, 403) and isinstance(error, dict)
                and f"mcp server url '{SERVER_HOST}' is not allowed." in str(error.get("message", "")).lower())


def evaluate(probes):
    healthy = all(probes[name].text_completed for name in CASES[:3])
    healthy = healthy and probes["allowed_metadata"].metadata_imported and probes["allowed_invoke"].tool_completed
    results = {}
    for name in CASES:
        reply = probes[name]
        if name in CASES[:5]:
            success = (reply.text_completed if name.endswith("_text") else
                       reply.metadata_imported if name.endswith("_metadata") else reply.tool_completed)
            state, reason = ("pass", "positive_control_succeeded") if success else ("blocked", "positive_control_failed")
        elif reply.metadata_imported or reply.tool_completed:
            state, reason = "fail", "forbidden_mcp_access_accepted"
        elif reply.policy_denied and healthy:
            state, reason = "pass", "explicit_mcp_domain_policy_rejection"
        else:
            state, reason = "blocked", "unverified_rejection_or_unhealthy_control"
        results[name] = {"state": state, "reason": reason, "http_status": reply.status}
    return results


def call(account, token, mode):
    payload = {"model": account["deployment"], "store": False, "max_output_tokens": 256,
               "input": "<task>Reply READY.</task>"}
    if account["model_properties"]["model"]["name"] == "gpt-5.1":
        payload["reasoning"] = {"effort": "none"}
    if mode != "text":
        payload["tools"] = [{"type": "mcp", "server_label": "public_microsoft_docs", "server_url": SERVER_URL,
                             "allowed_tools": ["microsoft_docs_search"],
                             "require_approval": "always" if mode == "metadata" else "never"}]
        payload["tool_choice"] = "none" if mode == "metadata" else "required"
        if mode == "invoke":
            payload["max_tool_calls"] = 1
            payload["input"] = ('<task>Call microsoft_docs_search once with query "Azure AI Foundry model deployment". '
                                'Then reply READY.</task>')
    request = urllib.request.Request(account["endpoint"] + "/openai/v1/responses", data=json.dumps(payload).encode(),
                                     headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        with foundry.opener().open(request, timeout=120) as response:
            body = json.loads(response.read(foundry.MAX_BODY))
            return Reply(response.status, body if isinstance(body, dict) else {})
    except urllib.error.HTTPError as error:
        try:
            body = json.loads(error.read(foundry.MAX_BODY))
        except (ValueError, UnicodeDecodeError):
            body = {}
        return Reply(error.code, body if isinstance(body, dict) else {})
    except (OSError, ValueError):
        return Reply(0, {})


def run_probes(config):
    before = foundry.verify_live(config, expected_fqdns=POLICIES)
    token = foundry.azure(["account", "get-access-token", "--resource", "https://ai.azure.com/"],
                          config["subscription_id"])["accessToken"]

    def account_probes(item):
        name, account = item
        return {name + "_" + mode: call(account, token, mode) for mode in ("text", "metadata", "invoke")}

    probes = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        for group in pool.map(account_probes, before.items()):
            probes.update(group)
    results = evaluate(probes)
    try:
        if before != foundry.verify_live(config, expected_fqdns=POLICIES):
            raise ValueError("Account or model settings changed during MCP probes")
    except (RuntimeError, ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError):
        for result in results.values():
            if result["state"] == "pass":
                result.update(state="blocked", reason="postflight_verification_failed")
    return results

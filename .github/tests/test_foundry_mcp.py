"""Offline tests for the existing Foundry suite's MCP policy checks."""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import pytest

from e2e_tests import test_foundry_mcp as live_tests
from e2e_tests.resources import foundry_mcp as mcp


ROOT = Path(__file__).resolve().parents[2]


def accepted(mode):
    items = {"text": {"type": "message", "content": [{"type": "output_text", "text": "READY"}]},
             "metadata": {"type": "mcp_list_tools", "tools": [{"name": "microsoft_docs_search"}]},
             "invoke": {"type": "mcp_call", "name": "microsoft_docs_search", "status": "completed", "error": None}}
    return mcp.Reply(200, {"status": "completed", "output": [items[mode]]})


def denied():
    return mcp.Reply(400, {"error": {"message": "MCP server url 'learn.microsoft.com' is not allowed. Allowed domains: deny-all.invalid."}})


def probes():
    return {name: accepted(name.rsplit("_", 1)[1]) if name in mcp.CASES[:5] else denied() for name in mcp.CASES}


class McpVerdictTests(unittest.TestCase):
    def test_explicit_rejections_with_healthy_controls_pass(self):
        self.assertTrue(all(result["state"] == "pass" for result in mcp.evaluate(probes()).values()))

    def test_imported_metadata_or_completed_tool_fails_restricted_cases(self):
        for name in mcp.CASES[5:]:
            for mode in ("metadata", "invoke"):
                with self.subTest(name=name, mode=mode):
                    values = probes()
                    values[name] = accepted(mode)
                    self.assertEqual(mcp.evaluate(values)[name]["state"], "fail")

    def test_unrelated_errors_and_throttling_are_inconclusive(self):
        for status in (0, 400, 401, 403, 404, 429, 500):
            values = probes()
            values["unrelated_metadata"] = mcp.Reply(status, {"error": {"message": "Request failed"}})
            self.assertEqual(mcp.evaluate(values)["unrelated_metadata"]["state"], "blocked")
        reply = denied()
        reply.status = 429
        self.assertFalse(reply.policy_denied)

    def test_each_positive_control_is_required(self):
        for name in mcp.CASES[:5]:
            values = probes()
            values[name] = mcp.Reply(429, {})
            self.assertTrue(all(mcp.evaluate(values)[key]["state"] == "blocked" for key in mcp.CASES[5:]))

    def test_unexpected_acceptance_survives_an_unhealthy_control(self):
        values = probes()
        values["allowed_text"] = mcp.Reply(429, {})
        values["empty_metadata"] = accepted("metadata")
        self.assertEqual(mcp.evaluate(values)["empty_metadata"]["state"], "fail")

    def test_approval_request_is_not_completed_tool_execution(self):
        reply = mcp.Reply(200, {"output": [{"type": "mcp_approval_request", "name": "microsoft_docs_search"}]})
        self.assertFalse(reply.tool_completed)
        for body in ({}, {"output": None}, {"output": [None]}, {"output": [{"type": "mcp_list_tools", "tools": []}]},
                     {"output": [{"type": "mcp_call", "name": "microsoft_docs_search", "status": "failed"}]}):
            value = mcp.Reply(200, body)
            self.assertFalse(value.metadata_imported)
            self.assertFalse(value.tool_completed)
            self.assertFalse(value.text_completed)

    def test_malformed_errors_are_inconclusive(self):
        for error in (None, [], "denied"):
            self.assertFalse(mcp.Reply(400, {"error": error}).policy_denied)


class McpProbeTests(unittest.TestCase):
    def test_request_separates_discovery_from_execution(self):
        target = {"endpoint": "https://synthetic.openai.azure.com", "deployment": "vision",
                  "model_properties": {"model": {"name": "gpt-5.1"}}}
        for mode in ("text", "metadata", "invoke"):
            with patch.object(mcp.foundry, "opener") as opener:
                response = opener.return_value.open.return_value.__enter__.return_value
                response.status = 200
                response.read.return_value = json.dumps(accepted(mode).body).encode()
                mcp.call(target, "synthetic-token", mode)
                request = opener.return_value.open.call_args.args[0]
                payload = json.loads(request.data)
                self.assertFalse(payload["store"])
                self.assertTrue(payload["input"].startswith("<task>"))
                if mode == "text":
                    self.assertNotIn("tools", payload)
                else:
                    self.assertEqual(payload["tools"][0]["server_url"], mcp.SERVER_URL)
                    self.assertEqual(payload["tools"][0]["allowed_tools"], ["microsoft_docs_search"])
                    self.assertEqual(payload["tool_choice"], "none" if mode == "metadata" else "required")
                    self.assertEqual(payload["tools"][0]["require_approval"], "always" if mode == "metadata" else "never")

    def test_policy_readback_and_postflight_drift(self):
        accounts = {name: {"label": name} for name in mcp.POLICIES}
        for changed in (False, True):
            after = copy.deepcopy(accounts)
            if changed:
                after["empty"]["changed"] = True
            with patch.object(mcp.foundry, "verify_live", side_effect=[accounts, after]) as verify, \
                    patch.object(mcp.foundry, "azure", return_value={"accessToken": "synthetic-token"}), \
                    patch.object(mcp, "call") as call:
                call.side_effect = lambda account, token, mode: accepted(mode) if account["label"] != "unrelated" else (
                    accepted(mode) if mode == "text" else denied())
                results = mcp.run_probes({"subscription_id": "synthetic"})
                self.assertEqual(call.call_count, 9)
                self.assertEqual(verify.call_args.kwargs["expected_fqdns"], mcp.POLICIES)
                self.assertEqual(results["empty_metadata"]["state"], "fail")
                self.assertEqual(results["unrelated_metadata"]["state"], "blocked" if changed else "pass")
                self.assertNotIn("synthetic-token", json.dumps(results))

    def test_parallel_workers_cannot_duplicate_probes(self):
        config = SimpleNamespace(workerinput={}, getoption=lambda _name: "accounts.json")
        with patch.object(mcp, "run_probes") as run, self.assertRaisesRegex(pytest.fail.Exception, "-n 0"):
            live_tests.foundry_mcp_results.__wrapped__(config)
        run.assert_not_called()

    def test_pytest_reports_failures_errors_and_skips(self):
        script = """
import json
import sys
from unittest.mock import patch
import pytest
from e2e_tests.resources import foundry_mcp
with patch.object(foundry_mcp, 'run_probes', return_value=json.loads(sys.argv[1])) as run:
    code = pytest.main(sys.argv[2:])
    if '--foundry-mcp-config' not in sys.argv:
        assert not run.called
    raise SystemExit(code)
"""
        for scenario, failures, errors, skips in (("accepted", 1, 0, 0), ("enforced", 0, 0, 0),
                                                  ("quota", 0, 5, 0), ("unconfigured", 0, 0, 9)):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                values = probes()
                if scenario == "accepted":
                    values["empty_metadata"] = accepted("metadata")
                elif scenario == "quota":
                    values["allowed_text"] = mcp.Reply(429, {})
                report = Path(directory) / "junit.xml"
                config = Path(directory) / "accounts.json"
                config.write_text("{}")
                args = [sys.executable, "-c", script, json.dumps(mcp.evaluate(values)), "-q", "-n", "0",
                        "test_foundry_mcp.py", f"--junitxml={report}"]
                if scenario != "unconfigured":
                    args.extend(["--foundry-mcp-config", str(config)])
                result = subprocess.run(args, cwd=ROOT / "e2e_tests", env={**os.environ, "PYTHONPATH": str(ROOT)},
                                        text=True, capture_output=True, timeout=60)
                self.assertEqual(result.returncode, 1 if failures or errors else 0, result.stdout + result.stderr)
                suite = ET.parse(report).getroot().find("testsuite")
                self.assertEqual(int(suite.attrib["tests"]), 9)
                self.assertEqual(int(suite.attrib["failures"]), failures)
                self.assertEqual(int(suite.attrib["errors"]), errors)
                self.assertEqual(int(suite.attrib["skipped"]), skips)

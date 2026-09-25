"""Offline coverage for the Foundry E2E probes and their pytest integration."""

import copy
import datetime as dt
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

from e2e_tests import test_foundry_egress as live_tests
from e2e_tests.resources import foundry


ROOT = Path(__file__).resolve().parents[2]
SUBSCRIPTION = "00000000-0000-0000-0000-000000000001"
TENANT = "00000000-0000-0000-0000-000000000002"


def success():
    return foundry.Reply(200, {"choices": [{"finish_reason": "stop", "message": {"content": "A red square."}}]})


def denial():
    return foundry.Reply(400, {"error": {"message": "Image URL domain is not allowed in this environment."}})


def probes():
    return {name: success() if name in foundry.CASES[:4] else denial() for name in foundry.CASES}


def configuration():
    prefix = f"/subscriptions/{SUBSCRIPTION}/resourceGroups/rg-test/providers/Microsoft.CognitiveServices/accounts/"
    return {"subscription_id": SUBSCRIPTION, "tenant_id": TENANT,
            "model_name": "gpt-5.1", "model_version": "2025-11-13",
            "accounts": {name: {"id": prefix + name, "deployment": "vision"}
                         for name in ("empty", "unrelated", "allowed")}}


def account(name="empty"):
    config = configuration()
    return {"id": config["accounts"][name]["id"], "kind": "AIServices",
            "systemData": {"lastModifiedAt": "2026-01-01T00:00:00Z"},
            "properties": {"provisioningState": "Succeeded", "restrictOutboundNetworkAccess": True,
                           "allowedFqdnList": foundry.verify_config(config)[name], "customSubDomainName": name}}


class VerdictTests(unittest.TestCase):
    def test_expected_policy_rejections_and_controls_pass(self):
        self.assertTrue(all(r["state"] == "pass" for r in foundry.evaluate(probes()).values()))

    def test_unexpected_image_acceptance_fails_for_both_allowlists(self):
        for name in foundry.CASES[4:]:
            values = probes()
            values[name] = success()
            self.assertEqual(foundry.evaluate(values)[name]["state"], "fail")

    def test_auth_quota_server_and_transport_errors_are_not_policy_passes(self):
        for status in (0, 401, 403, 404, 429, 500, 503):
            values = probes()
            values["empty_external"] = foundry.Reply(status, {"error": {"message": "Access denied"}})
            self.assertEqual(foundry.evaluate(values)["empty_external"]["state"], "blocked")

    def test_invalid_image_content_filter_and_inbound_firewall_are_not_policy_passes(self):
        for message in ("The provided image url is not accessible.", "The image size is not allowed.",
                        "Image URL was blocked by content filtering.", "Public network access is disabled.",
                        "Access denied due to Virtual Network/Firewall rules."):
            values = probes()
            values["empty_external"] = foundry.Reply(400, {"error": {"message": message}})
            self.assertEqual(foundry.evaluate(values)["empty_external"]["state"], "blocked")

    def test_policy_message_inside_429_does_not_pass(self):
        value = denial()
        value.status = 429
        self.assertFalse(value.policy_denied)

    def test_all_controls_are_required_for_an_empty_list_pass(self):
        for name in foundry.CASES[:-1]:
            values = probes()
            values[name] = foundry.Reply(429, {})
            self.assertEqual(foundry.evaluate(values)["empty_external"]["state"], "blocked")

    def test_unexpected_acceptance_is_retained_when_another_control_fails(self):
        values = probes()
        values["empty_external"] = success()
        values["allowed_inline"] = foundry.Reply(429, {})
        self.assertEqual(foundry.evaluate(values)["empty_external"]["state"], "fail")

    def test_truncated_or_filtered_completion_is_not_a_positive_control(self):
        for finish in ("length", "content_filter", None):
            value = success()
            value.body["choices"][0]["finish_reason"] = finish
            self.assertFalse(value.success)

    def test_malformed_success_payload_is_not_accepted(self):
        for body in ({}, {"choices": []}, {"choices": ["bad"]}, {"choices": [{"finish_reason": "stop"}]}):
            self.assertFalse(foundry.Reply(200, body).success)
        for content in (None, [], {}, "", " "):
            value = success()
            value.body["choices"][0]["message"]["content"] = content
            self.assertFalse(value.success)

    def test_malformed_error_payload_remains_inconclusive(self):
        for error in (None, "Bad request", ["bad request"]):
            self.assertFalse(foundry.Reply(400, {"error": error}).policy_denied)


class ReadbackTests(unittest.TestCase):
    def check(self, value):
        foundry.verify_account(value, configuration()["accounts"]["empty"]["id"], [],
                               now=dt.datetime(2026, 1, 1, 0, 16, tzinfo=dt.timezone.utc))

    def test_valid_readback_and_omitted_empty_list(self):
        value = account()
        self.check(value)
        del value["properties"]["allowedFqdnList"]
        self.check(value)

    def test_policy_drift_blocks_the_run(self):
        for key, changed in (("restrictOutboundNetworkAccess", False), ("allowedFqdnList", ["example.com"]),
                             ("provisioningState", "Updating")):
            value = account()
            value["properties"][key] = changed
            with self.assertRaises(ValueError):
                self.check(value)

    def test_last_change_not_creation_controls_propagation(self):
        value = account()
        value["systemData"] = {"createdAt": "2025-01-01T00:00:00Z", "lastModifiedAt": "2026-01-01T00:10:00Z"}
        with self.assertRaisesRegex(ValueError, "15 minutes"):
            self.check(value)

    def test_unknown_modification_time_is_not_assumed_settled(self):
        value = account()
        del value["systemData"]
        with self.assertRaises(ValueError):
            self.check(value)

    def test_wrong_subscription_and_resource_paths_are_rejected(self):
        for suffix in ("?api-version=evil", "/deployments/other", "#fragment"):
            config = configuration()
            config["accounts"]["empty"]["id"] += suffix
            with self.assertRaises(ValueError):
                foundry.verify_config(config)
        config = configuration()
        config["subscription_id"] = TENANT
        with self.assertRaises(ValueError):
            foundry.verify_config(config)

    def test_controls_must_use_three_distinct_accounts(self):
        config = configuration()
        config["accounts"]["empty"] = config["accounts"]["allowed"]
        with self.assertRaisesRegex(ValueError, "distinct"):
            foundry.verify_config(config)

    def test_invalid_matrix_is_rejected(self):
        config = configuration()
        del config["accounts"]["unrelated"]
        with self.assertRaises(ValueError):
            foundry.verify_config(config)

    def test_controls_may_be_in_different_resource_groups(self):
        config = configuration()
        config["accounts"]["empty"]["id"] = config["accounts"]["empty"]["id"].replace("rg-test", "rg-workspace")
        foundry.verify_config(config)

    @patch.object(foundry, "azure", return_value={"id": SUBSCRIPTION, "tenantId": TENANT})
    @patch.object(foundry, "arm")
    def test_live_readback_checks_policy_model_and_endpoint(self, arm, _azure):
        model = {"properties": {"provisioningState": "Succeeded",
                                "model": {"format": "OpenAI", "name": "gpt-5.1", "version": "2025-11-13"}}}

        def read(resource_id, _subscription):
            return model if "/deployments/" in resource_id else account(resource_id.rsplit("/", 1)[1])

        arm.side_effect = read
        self.assertEqual(foundry.verify_live(configuration())["empty"]["endpoint"], "https://empty.openai.azure.com")
        model["properties"]["model"]["version"] = "another-version"
        with self.assertRaisesRegex(ValueError, "model"):
            foundry.verify_live(configuration())


class ProbeTests(unittest.TestCase):
    def test_nonce_is_unique_per_run_and_case(self):
        urls = {foundry.image_url(foundry.DEFAULT_IMAGE, run_id, case)
                for run_id in ("run1", "run2") for case in ("empty", "allowed")}
        self.assertEqual(len(urls), 4)

    def test_credentials_and_signed_urls_are_rejected(self):
        for url in ("http://example.com/x.png", "https://user:password@example.com/x.png",
                    "https://example.com/x.png?sig=secret", "https://example.com:8443/x.png"):
            with self.assertRaises(ValueError):
                foundry.image_url(url, "run", "case")

    def test_inline_png_has_no_external_url(self):
        self.assertTrue(foundry.inline_image().startswith("data:image/png;base64,iVBOR"))

    def test_azure_cli_does_not_expose_error_output(self):
        completed = subprocess.CompletedProcess([], 1, "private-token", "private-token")
        with patch.object(foundry.subprocess, "run", return_value=completed), \
                self.assertRaisesRegex(RuntimeError, "^Azure CLI failed with exit code 1$"):
            foundry.azure(["account", "show"], SUBSCRIPTION)

    @patch.object(foundry, "check_image", return_value="image-hash")
    @patch.object(foundry, "verify_live")
    @patch.object(foundry, "azure", return_value={"accessToken": "private-token"})
    @patch.object(foundry, "call_model")
    def test_probes_preserve_unexpected_acceptance_on_postflight_drift(self, model, _azure, verify, _image):
        readback = {name: {"endpoint": name, "deployment": "vision"} for name in configuration()["accounts"]}

        def reply(target, image, _token, _model):
            return denial() if target["endpoint"] == "unrelated" and not image.startswith("data:") else success()

        model.side_effect = reply
        changed = copy.deepcopy(readback)
        changed["empty"]["deployment"] = "changed"
        for after in (readback, changed, ValueError("settings changed")):
            verify.side_effect = [readback, after]
            results = foundry.run_probes(configuration())
            self.assertEqual(results["empty_external"]["state"], "fail")
            self.assertEqual(sum(r["state"] == "pass" for r in results.values()), 5 if after == readback else 0)
            self.assertNotIn("private-token", json.dumps(results))


class PytestIntegrationTests(unittest.TestCase):
    def test_parallel_workers_cannot_duplicate_live_probes(self):
        config = SimpleNamespace(workerinput={}, getoption=lambda _name: "accounts.json")
        with patch.object(foundry, "run_probes") as run, self.assertRaisesRegex(pytest.fail.Exception, "-n 0"):
            live_tests.foundry_egress_results.__wrapped__(config)
        run.assert_not_called()

    def test_pytest_reports_failures_errors_and_opt_in_skips(self):
        # Run the real pytest fixtures without invoking Azure or the TRE lifecycle.
        script = """
import json
import sys
from unittest.mock import patch
import pytest
from e2e_tests.resources import foundry
results = json.loads(sys.argv[1])
with patch.object(foundry, 'run_probes', return_value=results) as run:
    code = pytest.main(sys.argv[2:])
    if '--foundry-egress-config' not in sys.argv:
        assert not run.called
    raise SystemExit(code)
"""
        for scenario, failures, errors, skips in (("unexpected_acceptance", 1, 0, 0), ("policy_enforced", 0, 0, 0),
                                                  ("quota", 0, 3, 0), ("unconfigured", 0, 0, 6),
                                                  ("bad_config", 0, 6, 0)):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                values = probes()
                if scenario == "unexpected_acceptance":
                    values["empty_external"] = success()
                elif scenario == "quota":
                    values["allowed_inline"] = foundry.Reply(429, {})
                output = Path(directory) / "junit.xml"
                config = Path(directory) / "accounts.json"
                config.write_text("invalid json" if scenario == "bad_config" else json.dumps(configuration()))
                args = [sys.executable, "-c", script, json.dumps(foundry.evaluate(values)),
                        "-q", "test_foundry_egress.py", "-m", "foundry_egress", f"--junitxml={output}"]
                if scenario != "unconfigured":
                    args += ["--foundry-egress-config", str(config)]
                environment = os.environ.copy()
                environment["PYTHONPATH"] = str(ROOT)
                result = subprocess.run(args, cwd=ROOT / "e2e_tests", env=environment,
                                        capture_output=True, text=True, timeout=60)
                self.assertEqual(result.returncode, 1 if failures or errors else 0, result.stdout + result.stderr)
                suite = ET.parse(output).getroot().find("testsuite")
                self.assertEqual(int(suite.attrib["tests"]), 6)
                self.assertEqual(int(suite.attrib["failures"]), failures)
                self.assertEqual(int(suite.attrib["errors"]), errors)
                self.assertEqual(int(suite.attrib["skipped"]), skips)


if __name__ == "__main__":
    unittest.main()

"""Check private certificate storage readiness without contacting Azure."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch


HELPER = Path(__file__).resolve().parents[2] / "templates/shared_services/certs/scripts/wait_for_private_storage.py"
SPEC = importlib.util.spec_from_file_location("certificate_storage_readiness", HELPER)
READINESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(READINESS)
HOSTNAME = "certificate.blob.core.windows.net"
PRIVATE_IP = "10.0.1.27"


class CertificateStorageReadinessTests(unittest.TestCase):
    def test_private_address_uses_verified_tls_and_storage_hostname(self):
        connection = MagicMock()
        context = MagicMock()
        answers = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (PRIVATE_IP, 443))]
        with (
            patch.object(READINESS.socket, "getaddrinfo", return_value=answers),
            patch.object(READINESS.socket, "create_connection", return_value=connection) as connect,
            patch.object(READINESS.ssl, "create_default_context", return_value=context),
        ):
            self.assertTrue(READINESS.probe(HOSTNAME, PRIVATE_IP)[0])
        connect.assert_called_once_with((PRIVATE_IP, 443), timeout=5)
        context.wrap_socket.assert_called_once_with(connection.__enter__.return_value, server_hostname=HOSTNAME)

    def test_public_mixed_empty_and_wrong_private_answers_never_connect(self):
        for addresses in ([], ["52.239.251.164"], [PRIVATE_IP, "52.239.251.164"], ["10.0.1.28"]):
            with self.subTest(addresses=addresses):
                answers = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443)) for address in addresses]
                with (
                    patch.object(READINESS.socket, "getaddrinfo", return_value=answers),
                    patch.object(READINESS.socket, "create_connection") as connect,
                ):
                    self.assertFalse(READINESS.probe(HOSTNAME, PRIVATE_IP)[0])
                    connect.assert_not_called()

    def test_lookup_failure_does_not_connect(self):
        with (
            patch.object(READINESS.socket, "getaddrinfo", side_effect=socket.gaierror("diagnostic detail")),
            patch.object(READINESS.socket, "create_connection") as connect,
        ):
            ready, reason = READINESS.probe(HOSTNAME, PRIVATE_IP)
        self.assertFalse(ready)
        self.assertIn("gaierror", reason)
        self.assertNotIn("diagnostic detail", reason)
        connect.assert_not_called()

    def test_tls_verification_failure_is_not_readiness(self):
        answers = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (PRIVATE_IP, 443))]
        with (
            patch.object(READINESS.socket, "getaddrinfo", return_value=answers),
            patch.object(
                READINESS.socket, "create_connection", side_effect=ssl.SSLCertVerificationError("private diagnostic")
            ),
        ):
            ready, reason = READINESS.probe(HOSTNAME, PRIVATE_IP)
        self.assertFalse(ready)
        self.assertIn("SSLCertVerificationError", reason)
        self.assertNotIn("private diagnostic", reason)

    def wait_with_results(self, results, **kwargs):
        elapsed = [0.0]

        def sleep(seconds):
            elapsed[0] += seconds

        with (
            patch.object(READINESS.time, "monotonic", side_effect=lambda: elapsed[0]),
            patch.object(READINESS.time, "sleep", side_effect=sleep),
            patch.object(READINESS, "run_probe", side_effect=results) as probe,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            READINESS.wait_for_private_storage(HOSTNAME, PRIVATE_IP, **kwargs)
        return probe.call_count, elapsed[0]

    def test_observed_dns_changes_restart_all_consecutive_checks(self):
        # Private, lookup error, private, public, private, public, then stable.
        results = [
            (ready, "private" if ready else "lookup or public DNS")
            for ready in [True, False, True, False, True, False] + [True] * 7
        ]
        count, elapsed = self.wait_with_results(results)
        self.assertEqual(count, 13)
        self.assertEqual(elapsed, 60)

    def test_sustained_readiness_spans_at_least_thirty_seconds(self):
        count, elapsed = self.wait_with_results([(True, "ready")] * 7)
        self.assertEqual(count, 7)
        self.assertEqual(elapsed, 30)

    def test_tls_failure_also_restarts_stability(self):
        results = [(True, "ready")] * 6 + [(False, "TLS check failed")] + [(True, "ready")] * 7
        count, elapsed = self.wait_with_results(results)
        self.assertEqual(count, 14)
        self.assertEqual(elapsed, 65)

    def test_timeout_prevents_unbounded_wait(self):
        with self.assertRaisesRegex(TimeoutError, "within 12 seconds"):
            self.wait_with_results([(False, "not ready")] * 3, timeout=12)

    def test_probe_gets_only_remaining_deadline(self):
        elapsed = [0.0]

        def consume_budget(hostname, expected_ip, timeout):
            self.assertEqual(timeout, 2)
            elapsed[0] += timeout
            return True, "too late"

        with (
            patch.object(READINESS.time, "monotonic", side_effect=lambda: elapsed[0]),
            patch.object(READINESS, "run_probe", side_effect=consume_budget),
            patch.object(READINESS.time, "sleep") as sleep,
        ):
            with self.assertRaises(TimeoutError):
                READINESS.wait_for_private_storage(HOSTNAME, PRIVATE_IP, timeout=2, required_successes=1)
            sleep.assert_not_called()

    def test_blocked_resolver_child_has_finite_timeout(self):
        with patch.object(READINESS.subprocess, "run", side_effect=subprocess.TimeoutExpired("probe", 2)) as run:
            ready, reason = READINESS.run_probe(HOSTNAME, PRIVATE_IP, 2)
        self.assertFalse(ready)
        self.assertIn("timed out", reason)
        self.assertEqual(run.call_args.kwargs["timeout"], 2)
        self.assertFalse(run.call_args.kwargs.get("shell", False))

    def test_invalid_child_results_cannot_report_readiness(self):
        for value, code in [
            ("not json", 0),
            ("[]", 0),
            ('{"ready":"yes","reason":"x"}', 0),
            ('{"ready":true,"reason":"x"}', 1),
            ("", 2),
        ]:
            with self.subTest(value=value, code=code):
                result = subprocess.CompletedProcess([], code, value, "internal diagnostic")
                with patch.object(READINESS.subprocess, "run", return_value=result):
                    ready, reason = READINESS.run_probe(HOSTNAME, PRIVATE_IP, 2)
                self.assertFalse(ready)
                self.assertNotIn("internal diagnostic", reason)

    def test_cli_rejects_public_and_special_expected_addresses(self):
        for address in ("52.239.251.164", "127.0.0.1", "169.254.169.254", "0.0.0.0", "invalid"):
            with self.subTest(address=address):
                result = subprocess.run(
                    [sys.executable, str(HELPER), "--hostname", HOSTNAME, "--expected-ip", address],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn("private endpoint IP address", result.stderr)

    def test_cli_failure_returns_nonzero(self):
        with (
            patch.object(sys, "argv", [str(HELPER), "--hostname", HOSTNAME, "--expected-ip", PRIVATE_IP]),
            patch.object(READINESS, "wait_for_private_storage", side_effect=TimeoutError("not ready")),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(READINESS.main(), 1)

    def test_probe_mode_reports_json_for_parent(self):
        output = io.StringIO()
        with (
            patch.object(sys, "argv", [str(HELPER), "--probe", "--hostname", HOSTNAME, "--expected-ip", PRIVATE_IP]),
            patch.object(READINESS, "probe", return_value=(False, "not ready")),
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(READINESS.main(), 1)
        self.assertEqual(json.loads(output.getvalue()), {"ready": False, "reason": "not ready"})


if __name__ == "__main__":
    unittest.main()

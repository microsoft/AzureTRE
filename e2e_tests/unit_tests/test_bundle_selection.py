"""Exercise the bundle selector and evidence boundary without Azure access."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

from e2e_tests import bundle_evidence, run_bundle


ROOT = run_bundle.REPO_ROOT
SQL = "tre-workspace-service-azuresql"
SQL_CASE = "test_azuresql.py::test_sql_query_survives_sku_upgrade"


class BundleSelectionTests(unittest.TestCase):
    def run_selector(self, *arguments, environment=None):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "result.json"
            env = os.environ.copy()
            for key in ("TEST_BUNDLE", "TEST_BUNDLE_REQUEST_FILE", "TEST_BUNDLE_MARKER", "E2E_TESTS_NUMBER_PROCESSES"):
                env.pop(key, None)
            env.update(environment or {})
            result = subprocess.run(
                [sys.executable, str(ROOT / "e2e_tests/run_bundle.py"), "--report", str(report), *arguments],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertTrue(report.exists(), result.stdout + result.stderr)
            return result, json.loads(report.read_text())

    def test_catalog_covers_the_actual_porter_inventory(self):
        catalog = run_bundle.load_catalog()
        manifests = {entry["manifest"] for entry in catalog.values()}
        self.assertEqual(manifests, {str(path.relative_to(ROOT)) for path in (ROOT / "templates").rglob("porter.yaml")})
        for name, entry in catalog.items():
            with self.subTest(bundle=name):
                self.assertTrue(entry["tests"] or entry["unavailable_reason"])
                self.assertTrue(entry["source_version"])
                self.assertTrue(entry["limitations"])

    def test_every_declared_case_collects_from_current_source(self):
        expected = sorted({node for entry in run_bundle.load_catalog().values() for node in entry["tests"]})
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join((str(ROOT), str(ROOT / "e2e_tests")))
        env.pop("PYTEST_ADDOPTS", None)
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", "-o", "addopts=", *expected],
            cwd=ROOT / "e2e_tests",
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        collected = sorted(line for line in result.stdout.splitlines() if line.startswith("test_") and "::" in line)
        self.assertEqual(collected, expected)

    def test_sql_collects_only_its_named_lifecycle_case(self):
        result, report = self.run_selector(
            "--bundle", SQL, "--collect-only", environment={"TEST_WORKSPACE_ID": "existing-workspace-id"}
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["collected_tests"], [SQL_CASE])
        self.assertEqual(report["status"], "not_run")
        self.assertFalse(report["full_lifecycle_proven"])
        self.assertEqual(report["resources"], [])
        self.assertEqual(report["configured_resource_ids"], {"TEST_WORKSPACE_ID": "existing-workspace-id"})
        self.assertIn("tre-workspace-base", report["declared_prerequisites"])

    def test_unknown_partial_and_shell_like_identifiers_fail_before_collection(self):
        for identifier in ("azuresql", "tre-nonexistent", SQL + "; echo unexpected", SQL + "$(echo unexpected)"):
            with self.subTest(identifier=identifier):
                result, report = self.run_selector("--bundle", identifier, "--validate-only")
                self.assertEqual(result.returncode, 2)
                self.assertIn("Unknown bundle identifier", result.stderr)
                self.assertEqual(report["status"], "selection_error")
                self.assertEqual(report["collected_tests"], [])

    def test_unavailable_bundle_fails_with_its_coverage_gap(self):
        result, report = self.run_selector("--bundle", "tre-user-resource-aml-compute-instance", "--validate-only")
        self.assertEqual(result.returncode, 2)
        self.assertIn("#5127", report["error"])
        self.assertEqual(report["collected_tests"], [])

    def test_marker_and_parallel_worker_inputs_are_rejected(self):
        for extra in ({"TEST_BUNDLE_MARKER": "workspace_services"}, {"E2E_TESTS_NUMBER_PROCESSES": "2"}):
            with self.subTest(environment=extra):
                result, report = self.run_selector("--bundle", SQL, "--validate-only", environment=extra)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(report["status"], "selection_error")

    def test_prepared_request_must_match_checkout_and_environment(self):
        cases = (
            ({"requested_checkout_sha": "0" * 40}, {}, "different checkout"),
            ({"tre_id": "another-tre"}, {"TRE_ID": "expected-tre"}, "different TRE"),
            ({"accept_nexus_eula": "false"}, {}, "must be a boolean"),
        )
        for change, extra_env, message in cases:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                prepared = run_bundle.request_from_environment(SQL)
                prepared.update(change)
                filename = Path(directory) / "request.json"
                filename.write_text(json.dumps(prepared))
                result, report = self.run_selector(
                    "--validate-only", environment={"TEST_BUNDLE_REQUEST_FILE": str(filename), **extra_env}
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn(message, report["error"])

    def test_request_metadata_does_not_copy_unknown_secret_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            prepared = run_bundle.request_from_environment(SQL)
            prepared["secret_password"] = "never-copy-this-value"
            filename = Path(directory) / "request.json"
            filename.write_text(json.dumps(prepared))
            result, report = self.run_selector(
                "--validate-only", environment={"TEST_BUNDLE_REQUEST_FILE": str(filename)}
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("never-copy-this-value", json.dumps(report))
            self.assertEqual(report["requested_tests"], [SQL_CASE])


class BundleEvidenceIntegrationTests(unittest.TestCase):
    def run_pytest(self, source, expected, selection=None):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "test_cases.py").write_text(textwrap.dedent(source))
            script = """
import json
import pytest
from pathlib import Path
from e2e_tests.bundle_evidence import BundleReport
settings = json.loads(Path("settings.json").read_text())
report = BundleReport("evidence.json", {"requested_tests": settings["expected"]})
code = pytest.main(["-q", *settings["selection"]], plugins=[report])
raise SystemExit(report.finish(code, False))
"""
            (folder / "runner.py").write_text(textwrap.dedent(script))
            (folder / "settings.json").write_text(
                json.dumps({"expected": expected, "selection": selection or expected})
            )
            env = os.environ.copy()
            env.update(PYTHONPATH=str(ROOT), PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
            env.pop("PYTEST_ADDOPTS", None)
            result = subprocess.run(
                [sys.executable, "runner.py"],
                cwd=folder,
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            self.assertTrue((folder / "evidence.json").exists(), result.stdout + result.stderr)
            return result, json.loads((folder / "evidence.json").read_text())

    def test_parameter_selection_does_not_execute_other_bundles(self):
        source = """
import pytest
@pytest.mark.parametrize("bundle", ["sql", "unrelated"])
def test_bundle(bundle):
    assert bundle == "sql", "an unrelated bundle was executed"
"""
        node = "test_cases.py::test_bundle[sql]"
        result, report = self.run_pytest(source, [node])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["collected_tests"], [node])
        self.assertEqual(report["counts"]["passed"], 1)
        self.assertEqual(report["status"], "passed_selected_cases")
        self.assertFalse(report["full_lifecycle_proven"])

    def test_all_skipped_is_reported_and_does_not_pass(self):
        result, report = self.run_pytest(
            'import pytest\n@pytest.mark.skip(reason="missing prerequisite")\ndef test_bundle(): pass\n',
            ["test_cases.py::test_bundle"],
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["status"], "skipped")
        self.assertEqual(report["counts"]["skipped"], 1)
        self.assertIn("missing prerequisite", report["test_results"][0]["reason"])

    def test_teardown_failure_is_not_a_bundle_pass(self):
        source = """
import pytest
@pytest.fixture
def resource():
    yield
    raise RuntimeError("secret-in-existing-traceback")
def test_bundle(resource): pass
"""
        result, report = self.run_pytest(source, ["test_cases.py::test_bundle"])
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["counts"]["passed"], 1)
        self.assertEqual(report["counts"]["errors"], 1)
        self.assertNotIn("secret-in-existing-traceback", json.dumps(report))

    def test_missing_or_extra_collected_cases_fail(self):
        source = "def test_bundle(): pass\ndef test_other(): pass\n"
        for requested in (["test_cases.py::test_missing"], ["test_cases.py"]):
            with self.subTest(requested=requested):
                result, report = self.run_pytest(source, ["test_cases.py::test_bundle"], requested)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(report["status"], "failed")

    def test_zero_collected_cases_fail(self):
        result, report = self.run_pytest("", [], ["test_cases.py"])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["collected_tests"], [])

    def test_resource_journal_records_ids_without_properties_or_tokens(self):
        with tempfile.TemporaryDirectory() as directory:
            report = bundle_evidence.BundleReport(Path(directory) / "evidence.json", {})
            bundle_evidence.activate(report)
            try:
                bundle_evidence.record_resource(
                    {"templateName": SQL, "properties": {"password": "secret-value"}},
                    {
                        "id": "op-id",
                        "resourceId": "sql-id",
                        "resourcePath": "/workspaces/ws/services/sql-id",
                        "message": "secret-value",
                    },
                    "POST",
                )
                bundle_evidence.record_operation(
                    "https://tre.example/api/operations/op-id?sig=secret-value", "deployed", True
                )
            finally:
                bundle_evidence.activate(None)
            self.assertEqual(report.data["resources"][0]["resourceId"], "sql-id")
            self.assertTrue(report.data["operations"]["/api/operations/op-id"]["done"])
            self.assertNotIn("secret-value", report.filename.read_text())


if __name__ == "__main__":
    unittest.main()

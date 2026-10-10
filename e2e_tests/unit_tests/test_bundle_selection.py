"""Exercise the bundle selector and evidence boundary without Azure access."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch

from e2e_tests import bundle_evidence, run_bundle


ROOT = run_bundle.REPO_ROOT
SQL = "tre-workspace-service-azuresql"
SQL_CASE = "test_azuresql.py::test_sql_query_survives_sku_upgrade"


class BundleSelectionTests(unittest.TestCase):
    def prepared_request(self):
        request = run_bundle.request_from_environment(SQL)
        request.update(tre_id="tre-test", location="switzerlandnorth", cloud="AzureCloud")
        return request

    def run_prepared_request(self, prepared, *arguments, environment=None):
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "request.json"
            filename.write_text(json.dumps(prepared))
            return self.run_selector(
                *arguments, environment={"TEST_BUNDLE_REQUEST_FILE": str(filename), **(environment or {})}
            )

    def run_selector(self, *arguments, environment=None, relative_report=False):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "result.json"
            env = os.environ.copy()
            for key in (
                "TEST_BUNDLE",
                "TEST_BUNDLE_REQUEST_FILE",
                "TEST_BUNDLE_MARKER",
                "E2E_TESTS_NUMBER_PROCESSES",
                "TRE_ID",
                "LOCATION",
                "AZURE_ENVIRONMENT",
            ):
                env.pop(key, None)
            env.update(environment or {})
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "e2e_tests/run_bundle.py"),
                    "--report",
                    report.name if relative_report else str(report),
                    *arguments,
                ],
                cwd=directory if relative_report else ROOT,
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

    def test_relative_report_reaches_final_status_in_the_caller_directory(self):
        result, report = self.run_selector("--bundle", SQL, "--collect-only", relative_report=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["collected_tests"], [SQL_CASE])
        self.assertEqual(report["status"], "not_run")
        self.assertFalse(report["full_lifecycle_proven"])

    def test_base_workspace_collects_its_own_case_without_reusing_a_workspace(self):
        result, report = self.run_selector(
            "--bundle",
            "tre-workspace-base",
            "--collect-only",
            environment={"TEST_WORKSPACE_ID": "existing-unrelated-workspace"},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["collected_tests"], ["test_workspace_base.py::test_base_workspace_lifecycle"])
        self.assertEqual(report["status"], "not_run")
        self.assertFalse(report["full_lifecycle_proven"])
        self.assertEqual(report["resources"], [])
        self.assertEqual(report["declared_prerequisites"], {})

    def test_unknown_partial_and_shell_like_identifiers_fail_before_collection(self):
        for identifier in ("azuresql", "tre-nonexistent", SQL + "; echo unexpected", SQL + "$(echo unexpected)"):
            with self.subTest(identifier=identifier):
                result, report = self.run_selector("--bundle", identifier, "--validate-only")
                self.assertEqual(result.returncode, 2)
                self.assertIn("Unknown bundle identifier", result.stderr)
                self.assertEqual(report["status"], "selection_error")
                self.assertEqual(report["collected_tests"], [])

    def test_certificate_and_nexus_selections_keep_target_and_dependency_evidence_separate(self):
        firewall = "tre-shared-service-firewall"
        certificate = "tre-shared-service-certs"
        cases = (
            (certificate, "test_create_certificate_shared_service", {firewall}),
            ("tre-shared-service-sonatype-nexus", "test_create_certs_nexus_shared_service", {firewall, certificate}),
        )
        for bundle, case, prerequisites in cases:
            with self.subTest(bundle=bundle):
                result, report = self.run_selector("--bundle", bundle, "--collect-only")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(report["collected_tests"], ["test_shared_services.py::" + case])
                self.assertEqual(set(report["declared_prerequisites"]), prerequisites)
                self.assertEqual(report["status"], "not_run")
                self.assertFalse(report["full_lifecycle_proven"])
                self.assertEqual(report["resources"], [])

    def test_shared_service_suite_does_not_add_another_certificate_request(self):
        env = dict(os.environ, PYTHONPATH=os.pathsep.join((str(ROOT), str(ROOT / "e2e_tests"))))
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "--collect-only",
                "-q",
                "-o",
                "addopts=",
                "-m",
                "shared_services",
                "test_shared_services.py",
            ],
            cwd=ROOT / "e2e_tests",
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        collected = [line for line in result.stdout.splitlines() if line.startswith("test_shared_services.py::")]
        self.assertEqual(len(collected), 5)
        self.assertIn("test_shared_services.py::test_create_certs_nexus_shared_service", collected)
        self.assertNotIn("test_shared_services.py::test_create_certificate_shared_service", collected)

    def test_unavailable_bundle_fails_with_its_coverage_gap(self):
        result, report = self.run_selector("--bundle", "tre-user-resource-aml-compute-instance", "--validate-only")
        self.assertEqual(result.returncode, 2)
        self.assertIn("#5127", report["error"])
        self.assertEqual(report["collected_tests"], [])

    def test_openai_selects_the_guarded_case_and_reports_remaining_coverage(self):
        result, report = self.run_selector("--bundle", "tre-workspace-service-openai", "--collect-only")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["collected_tests"], ["test_openai.py::test_private_openai_lifecycle"])
        self.assertEqual(report["status"], "not_run")
        self.assertFalse(report["full_lifecycle_proven"])
        self.assertEqual(report["source_bundle_version"], "1.1.0")
        self.assertIn("tre-workspace-base", report["declared_prerequisites"])

    def test_export_review_selects_only_its_private_lifecycle(self):
        result, report = self.run_selector("--bundle", "tre-service-guacamole-export-reviewvm", "--collect-only")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            report["collected_tests"], ["test_airlock_export_review.py::test_airlock_export_review_vm_flow"]
        )
        self.assertEqual(report["status"], "not_run")
        self.assertFalse(report["full_lifecycle_proven"])
        self.assertIn("tre-service-guacamole-windowsvm", report["declared_prerequisites"])
        self.assertIn("synthetic-review-data", report["coverage"])

    def test_observed_deployment_evidence_excludes_properties(self):
        with tempfile.TemporaryDirectory() as directory:
            report = bundle_evidence.BundleReport(Path(directory) / "report.json", {})
            with patch.object(bundle_evidence, "_ACTIVE_REPORT", report):
                bundle_evidence.record_deployed_resource(
                    {
                        "id": "vm",
                        "templateName": "review",
                        "templateVersion": "2.0.9",
                        "properties": {"secret": "excluded"},
                    },
                    "/workspaces/ws/workspace-services/service/user-resources/vm",
                )
            self.assertEqual(
                report.data["resources"],
                [
                    {
                        "method": "GET",
                        "resourceId": "vm",
                        "resourcePath": "/workspaces/ws/workspace-services/service/user-resources/vm",
                        "bundle": "review",
                        "deployed_template_version": "2.0.9",
                    }
                ],
            )

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
            ({"location": "eastus"}, {"LOCATION": "switzerlandnorth"}, "different TRE"),
            ({"cloud": "AzureUSGovernment"}, {"AZURE_ENVIRONMENT": "AzureCloud"}, "different TRE"),
            ({"accept_nexus_eula": "false"}, {}, "must be a boolean"),
        )
        for change, extra_env, message in cases:
            with self.subTest(change=change):
                prepared = self.prepared_request()
                prepared.update(change)
                result, report = self.run_prepared_request(prepared, "--validate-only", environment=extra_env)
                self.assertEqual(result.returncode, 2)
                self.assertIn(message, report["error"])

    def test_missing_request_fields_are_not_filled_from_the_current_environment(self):
        complete = self.prepared_request()
        for field in complete:
            with self.subTest(field=field):
                prepared = {key: value for key, value in complete.items() if key != field}
                result, report = self.run_prepared_request(
                    prepared,
                    "--collect-only",
                    environment={
                        "TRE_ID": "tre-test",
                        "LOCATION": "switzerlandnorth",
                        "AZURE_ENVIRONMENT": "AzureCloud",
                    },
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn(f"missing required field: {field}", report["error"])
                self.assertEqual(report["collected_tests"], [])

    def test_invalid_prepared_request_shape_and_types_fail_before_collection(self):
        for prepared in (None, [], "invalid", 1):
            with self.subTest(prepared=prepared):
                result, report = self.run_prepared_request(prepared, "--collect-only")
                self.assertEqual(result.returncode, 2)
                self.assertIn("JSON object", report["error"])
                self.assertEqual(report["collected_tests"], [])
        for field in run_bundle.REQUEST_STRING_FIELDS:
            with self.subTest(field=field):
                prepared = {**self.prepared_request(), field: None}
                result, report = self.run_prepared_request(prepared, "--collect-only")
                self.assertEqual(result.returncode, 2)
                self.assertIn(f"{field} must be a string", report["error"])
                self.assertEqual(report["collected_tests"], [])

    def test_prepared_request_requires_checkout_and_environment_identifiers(self):
        for field in ("requested_checkout_sha", "tre_id", "location", "cloud"):
            with self.subTest(field=field):
                prepared = {**self.prepared_request(), field: " "}
                result, report = self.run_prepared_request(prepared, "--collect-only")
                self.assertEqual(result.returncode, 2)
                self.assertEqual(report["status"], "selection_error")
                self.assertEqual(report["collected_tests"], [])

    def test_generated_request_round_trips_without_replacing_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "request.json"
            environment = {
                "PATH": os.environ["PATH"],
                "TRE_ID": "tre-test",
                "LOCATION": "switzerlandnorth",
                "AZURE_ENVIRONMENT": "AzureCloud",
                "GITHUB_RUN_ID": "original-run",
            }
            with patch.dict(os.environ, environment, clear=True), patch.object(run_bundle, "REQUEST_FILE", filename):
                code = run_bundle.main(["--bundle", SQL, "--prepare", "--report", str(Path(directory) / "report.json")])
            self.assertEqual(code, 0)
            prepared = json.loads(filename.read_text())
            result, report = self.run_prepared_request(
                prepared, "--collect-only", environment={"GITHUB_RUN_ID": "current-run"}
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(report["provenance"], prepared)
            self.assertEqual(report["collected_tests"], [SQL_CASE])

    def test_review_vm_inventory_includes_bootstrap_prerequisites(self):
        catalog = run_bundle.load_catalog()
        for bundle in ("tre-service-guacamole-import-reviewvm", "tre-service-guacamole-export-reviewvm"):
            with self.subTest(bundle=bundle):
                self.assertLessEqual(
                    {"tre-shared-service-certs", "tre-shared-service-sonatype-nexus"},
                    set(catalog[bundle]["prerequisites"]),
                )

    def test_request_metadata_does_not_copy_unknown_secret_fields(self):
        prepared = self.prepared_request()
        prepared["secret_password"] = "never-copy-this-value"
        result, report = self.run_prepared_request(prepared, "--validate-only")
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

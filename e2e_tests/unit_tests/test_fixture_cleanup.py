"""Check real session fixtures against the pinned pytest timeout plugins."""

import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import AsyncMock
import xml.etree.ElementTree as ET

from e2e_tests.resources import resource


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_STUBS = """
import asyncio
import json
import time
from pathlib import Path
import pytest
from e2e_tests import conftest as fixtures
from contextlib import asynccontextmanager

@asynccontextmanager
async def nexus_prerequisites(verify):
    if settings.get("record_nexus"):
        event(["nexus", "ready"])
    try:
        yield
    finally:
        if settings.get("record_nexus"):
            event(["nexus", "delete"])

fixtures.nexus_prerequisites = nexus_prerequisites

settings = json.loads(Path("settings.json").read_text())
fixtures.CLEANUP_TIMEOUT_SECONDS = settings["budget"]

def event(value):
    with Path("events.jsonl").open("a") as log:
        log.write(json.dumps(value) + "\\n")

async def create_workspace(**kwargs):
    name = "review" if "review" in kwargs.get("template_name", "") else "research"
    return f"/workspaces/{name}", name

async def token(*args, **kwargs):
    return "offline-token"

async def auth_details(*args, **kwargs):
    return "offline-workspace-token", {}

async def create_service(*args, **kwargs):
    if settings.get("fail_service_setup"):
        raise RuntimeError("SERVICE_SETUP_FAILED")
    return "/workspaces/review/workspace-services/service", "service"

async def delete_resource(resource_path, *args):
    name = resource_path.rsplit("/", 1)[1]
    event([name, "start"])
    try:
        if name == settings.get("failure_resource"):
            raise RuntimeError("DELETE_FAILED")
        await asyncio.sleep(settings["durations"].get(name, 0.01))
        event([name, "complete"])
    except asyncio.CancelledError:
        event([name, "cancel"])
        # The next fixture must wait for asynchronous cancellation to finish.
        await asyncio.sleep(0.03)
        event([name, "cancel_complete"])
        raise
    finally:
        event([name, "finish"])

fixtures.create_or_get_test_workspace = create_workspace
fixtures.get_admin_token = token
fixtures.get_workspace_auth_details = auth_details
fixtures.create_or_get_test_workpace_service = create_service
fixtures.disable_and_delete_tre_resource = delete_resource
fixtures.disable_and_delete_ws_resource = delete_resource
fixtures.config.TEST_WORKSPACE_ID = ""
fixtures.config.TEST_WORKSPACE_SERVICE_ID = ""
fixtures.config.TEST_AAD_WORKSPACE_ID = ""
fixtures.config.TEST_AIRLOCK_IMPORT_REVIEW_WORKSPACE_ID = ""
fixtures.config.TEST_AIRLOCK_IMPORT_REVIEW_WORKSPACE_SERVICE_ID = ""

# Register the actual fixtures and hooks, with only Azure calls replaced.
setup_nexus_prerequisites = fixtures.setup_nexus_prerequisites
setup_test_workspace = fixtures.setup_test_workspace
setup_test_workspace_and_guacamole_service = fixtures.setup_test_workspace_and_guacamole_service
setup_test_aad_workspace = fixtures.setup_test_aad_workspace
setup_test_airlock_import_review_workspace_and_guacamole_service = (
    fixtures.setup_test_airlock_import_review_workspace_and_guacamole_service
)
pytest_timeout_set_timer = fixtures.pytest_timeout_set_timer
pytest_timeout_cancel_timer = fixtures.pytest_timeout_cancel_timer
pytest_runtest_teardown = fixtures.pytest_runtest_teardown
pytest_runtest_makereport = fixtures.pytest_runtest_makereport

class SlowReportPlugin:
    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        yield
        if call.when == "teardown" and settings.get("slow_report"):
            time.sleep(0.2)

def pytest_configure(config):
    config.pluginmanager.register(SlowReportPlugin())

@pytest.fixture(scope="session")
def verify():
    return True
"""
RESOURCE_TEST = """
@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.timeout(0.1)
async def test_resources(
    setup_test_workspace,
    setup_test_airlock_import_review_workspace_and_guacamole_service,
):
    assert setup_test_workspace[1] == "research"
    assert setup_test_airlock_import_review_workspace_and_guacamole_service[1] == "review"
"""
UNRELATED_TEST = """
@pytest.mark.timeout(0.1)
def test_unrelated():
    assert True
"""


class FixtureCleanupIntegrationTests(unittest.TestCase):
    def run_pytest(
        self,
        test_source,
        *,
        budget=1,
        durations=None,
        failure_resource=None,
        record_nexus=False,
        fail_service_setup=False,
        slow_report=False,
    ):
        settings = {
            "budget": budget,
            "durations": durations or {"review": 0.2, "research": 0.2},
            "failure_resource": failure_resource,
            "record_nexus": record_nexus,
            "fail_service_setup": fail_service_setup,
            "slow_report": slow_report,
        }
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "conftest.py").write_text(textwrap.dedent(FIXTURE_STUBS))
            (folder / "test_cases.py").write_text(
                "import time\nimport pytest\nimport asyncio\nfrom conftest import event\nfrom e2e_tests.timeouts import async_test_timeout\n"
                + test_source
            )
            (folder / "settings.json").write_text(json.dumps(settings))
            environment = os.environ.copy()
            environment["PYTHONPATH"] = os.pathsep.join((str(REPO_ROOT), str(REPO_ROOT / "e2e_tests")))
            environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
            environment.pop("PYTEST_ADDOPTS", None)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-p",
                    "pytest_asyncio.plugin",
                    "-p",
                    "pytest_timeout",
                    "-o",
                    "asyncio_mode=auto",
                    "-o",
                    "asyncio_default_fixture_loop_scope=session",
                    "--junitxml=results.xml",
                    "--tb=short",
                    "-q",
                    "test_cases.py",
                ],
                cwd=directory,
                env=environment,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            self.assertTrue((folder / "results.xml").exists(), result.stdout + result.stderr)
            report = ET.parse(folder / "results.xml").getroot()
            events_file = folder / "events.jsonl"
            events = [json.loads(line) for line in events_file.read_text().splitlines()] if events_file.exists() else []
            return result, report, events

    def assert_sequential_cleanup(self, events):
        self.assertEqual(
            events,
            [
                ["review", "start"],
                ["review", "complete"],
                ["review", "finish"],
                ["research", "start"],
                ["research", "complete"],
                ["research", "finish"],
            ],
        )

    def test_slow_cleanup_does_not_inherit_last_test_budget_in_either_order(self):
        for source in (RESOURCE_TEST + UNRELATED_TEST, UNRELATED_TEST + RESOURCE_TEST):
            with self.subTest(order=source):
                result, report, events = self.run_pytest(source)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(len(report.findall(".//testcase")), 2)
                self.assert_sequential_cleanup(events)

    def test_nexus_outlives_review_workspace_cleanup(self):
        result, _, events = self.run_pytest(RESOURCE_TEST, record_nexus=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertLess(events.index(["nexus", "ready"]), events.index(["review", "start"]))
        self.assertLess(events.index(["review", "complete"]), events.index(["nexus", "delete"]))

    def test_restored_timer_does_not_interrupt_teardown_error_reporting(self):
        result, report, events = self.run_pytest(RESOURCE_TEST, failure_resource="review", slow_report=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(len(report.findall(".//error")), 1)
        self.assertIn("DELETE_FAILED", result.stdout)
        self.assertNotIn("INTERNALERROR", result.stdout)
        self.assertIn(["research", "complete"], events)

    def test_service_setup_failure_still_cleans_up_review_workspace_before_nexus(self):
        source = RESOURCE_TEST.replace("@pytest.mark.timeout(0.1)", "@pytest.mark.timeout(1, func_only=True)")
        result, report, events = self.run_pytest(source, record_nexus=True, fail_service_setup=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("SERVICE_SETUP_FAILED", result.stdout)
        self.assertEqual(len(report.findall(".//error")), 1)
        self.assertLess(events.index(["review", "complete"]), events.index(["nexus", "delete"]))
        self.assertIn(["research", "complete"], events)

    def test_cleanup_timeout_finishes_cancellation_before_next_fixture(self):
        # Keep the independent cleanup deadline short, but leave enough time
        # for pytest to format its expected error on slower CI runners.
        source = (RESOURCE_TEST + UNRELATED_TEST).replace("@pytest.mark.timeout(0.1)", "@pytest.mark.timeout(1)")
        result, report, events = self.run_pytest(
            source,
            budget=0.05,
            durations={"review": 1, "research": 0.01},
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(len(report.findall(".//error")), 1)
        self.assertIn("Cleanup of /workspaces/review exceeded 0.05 seconds", result.stdout)
        self.assertEqual(
            events,
            [
                ["review", "start"],
                ["review", "cancel"],
                ["review", "cancel_complete"],
                ["review", "finish"],
                ["research", "start"],
                ["research", "complete"],
                ["research", "finish"],
            ],
        )

    def test_body_and_cleanup_failures_are_both_reported(self):
        source = (
            RESOURCE_TEST
            + """
@pytest.mark.timeout(0.1)
def test_failure():
    assert False, "BODY_FAILED"
"""
        )
        result, report, events = self.run_pytest(source, failure_resource="review")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(len(report.findall(".//failure")), 1)
        self.assertEqual(len(report.findall(".//error")), 1)
        self.assertIn("BODY_FAILED", result.stdout)
        self.assertIn("DELETE_FAILED", result.stdout)
        self.assertIn(["research", "complete"], events)

    def test_body_timeout_remains_failure_and_session_cleanup_finishes(self):
        source = (
            RESOURCE_TEST
            + """
@pytest.mark.timeout(0.05)
def test_body_timeout():
    time.sleep(1)
"""
        )
        result, report, events = self.run_pytest(source)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(len(report.findall(".//failure")), 1)
        self.assertEqual(len(report.findall(".//error")), 0)
        self.assertIn("Timeout >0.05s", result.stdout)
        self.assert_sequential_cleanup(events)

    def test_async_body_timeout_cancels_polling_before_next_test_and_cleanup(self):
        source = (
            RESOURCE_TEST
            + """
@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.timeout(1)
@async_test_timeout(0.02)
async def test_async_timeout():
    try:
        await asyncio.sleep(10)
        event(["body", "leaked"])
    finally:
        await asyncio.sleep(0.03)
        event(["body", "cancel_complete"])

@pytest.mark.asyncio(loop_scope="session")
async def test_after_timeout():
    event(["next", "start"])
    await asyncio.sleep(0.05)
"""
        )
        result, report, events = self.run_pytest(source)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(len(report.findall(".//failure")), 1)
        self.assertEqual(len(report.findall(".//error")), 0)
        self.assertIn("TimeoutError", result.stdout)
        self.assertEqual(events[:2], [["body", "cancel_complete"], ["next", "start"]])
        self.assert_sequential_cleanup(events[2:])
        self.assertNotIn("Task exception was never retrieved", result.stdout + result.stderr)

    def test_setup_timeout_remains_error_and_session_cleanup_finishes(self):
        source = (
            RESOURCE_TEST
            + """
@pytest.fixture
def slow_setup():
    time.sleep(1)

@pytest.mark.timeout(0.05)
def test_setup_timeout(slow_setup):
    assert False, "body must not run"
"""
        )
        result, report, events = self.run_pytest(source)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(len(report.findall(".//error")), 1)
        self.assertIn("Timeout >0.05s", result.stdout)
        self.assert_sequential_cleanup(events)

    def test_unmanaged_fixture_teardown_keeps_test_timeout(self):
        source = """
@pytest.fixture
def unmanaged_fixture():
    yield
    time.sleep(1)

@pytest.mark.timeout(0.05)
def test_unmanaged(unmanaged_fixture):
    assert True
"""
        result, report, events = self.run_pytest(source)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(len(report.findall(".//error")), 1)
        self.assertIn("Timeout >0.05s", result.stdout)
        self.assertEqual(events, [])

    def test_workspace_service_cleanup_has_independent_timeout(self):
        source = """
@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.timeout(1)
async def test_service(setup_test_workspace_and_guacamole_service):
    assert setup_test_workspace_and_guacamole_service[3] == "service"
"""
        result, report, events = self.run_pytest(
            source,
            budget=0.05,
            durations={"service": 1, "research": 0.01},
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(len(report.findall(".//error")), 1)
        self.assertIn("Cleanup of /workspaces/review/workspace-services/service exceeded 0.05 seconds", result.stdout)
        self.assertLess(events.index(["service", "cancel_complete"]), events.index(["research", "start"]))

    def test_unmanaged_function_finalizer_keeps_timeout_before_managed_cleanup(self):
        source = (
            RESOURCE_TEST
            + """
@pytest.fixture
def unmanaged_fixture():
    yield
    event(["unmanaged", "start"])
    time.sleep(1)
    event(["unmanaged", "leaked"])

@pytest.mark.timeout(0.05)
def test_last(unmanaged_fixture):
    assert True
"""
        )
        result, report, events = self.run_pytest(source)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(len(report.findall(".//error")), 1)
        self.assertIn("Timeout >0.05s", result.stdout)
        self.assertEqual(events[0], ["unmanaged", "start"])
        self.assert_sequential_cleanup(events[1:])

    def test_unmanaged_session_finalizer_keeps_timeout_after_managed_cleanup(self):
        source = """
@pytest.fixture(scope="session")
def unmanaged_fixture():
    yield
    event(["unmanaged", "start"])
    time.sleep(1)
    event(["unmanaged", "leaked"])
""" + RESOURCE_TEST.replace("    setup_test_workspace,", "    unmanaged_fixture,\n    setup_test_workspace,")
        result, report, events = self.run_pytest(source)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(len(report.findall(".//error")), 1)
        self.assertIn("Timeout >", result.stdout)
        self.assert_sequential_cleanup(events[:-1])
        self.assertEqual(events[-1], ["unmanaged", "start"])


class CleanupPollingDiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancellation_records_last_observed_operation_state(self):
        check = AsyncMock(return_value=(False, "pipeline_running", "Waiting for resource", "Step 1"))
        with self.assertLogs(resource.LOGGER, level="ERROR") as logs:
            with self.assertRaises(TimeoutError):
                async with asyncio.timeout(0.01):
                    await resource.wait_for(check, None, "/api/operations/cleanup", "token", [])
        self.assertIn("/api/operations/cleanup", logs.output[0])
        self.assertIn("pipeline_running", logs.output[0])
        self.assertIn("Waiting for resource", logs.output[0])

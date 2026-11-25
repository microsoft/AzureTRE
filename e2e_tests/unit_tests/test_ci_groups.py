"""Exercise CI group collection, isolation and execution without Azure."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from e2e_tests import ci_groups


SOURCE = """
from pathlib import Path
import pytest

@pytest.mark.shared_services
def test_other():
    Path("other-ran").touch()

@pytest.mark.shared_services
@pytest.mark.nexus
def test_nexus():
    Path("nexus-ran").touch()
"""


class CIGroupsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        (self.folder / "test_cases.py").write_text(SOURCE)
        (self.folder / "conftest.py").write_text(
            'def pytest_addoption(parser):\n    parser.addoption("--verify", default="true")\n'
        )
        (self.folder / "pytest.ini").write_text("[pytest]\nmarkers =\n    shared_services\n    nexus\n")
        self.output = self.folder / "output"

    def invoke(self, *args, extra=None):
        environment = dict(
            os.environ,
            PYTHONPATH=os.pathsep.join((str(ci_groups.ROOT), str(ci_groups.E2E_ROOT))),
            GITHUB_OUTPUT=str(self.output),
            E2E_TESTS_NUMBER_PROCESSES="1",
        )
        environment.pop("E2E_CI_GROUP_FILE", None)
        environment.update(extra or {})
        script = (
            "from pathlib import Path; from e2e_tests import ci_groups; "
            "ci_groups.E2E_ROOT = Path.cwd(); raise SystemExit(ci_groups.main())"
        )
        return subprocess.run(
            [sys.executable, "-c", script, *args],
            cwd=self.folder,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    def plan(self, selector="shared_services"):
        result = self.invoke("--plan", extra={"E2E_SELECTOR": selector})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(self.output.read_text().split("groups=")[-1])

    def run_group(self, group, **kwargs):
        filename = self.folder / "request.json"
        filename.write_text(json.dumps(group))
        return self.invoke("--run", str(filename), **kwargs)

    def test_selected_cases_are_partitioned_without_loss_or_overlap(self):
        groups = self.plan()
        self.assertEqual([g["name"] for g in groups], ["other", "nexus"])
        self.assertEqual(groups[0]["tests"], ["test_cases.py::test_other"])
        self.assertEqual(groups[1]["tests"], ["test_cases.py::test_nexus"])
        self.assertFalse((self.folder / "other-ran").exists())
        self.assertFalse((self.folder / "nexus-ran").exists())

    def test_empty_groups_are_omitted_and_empty_selection_fails(self):
        self.assertEqual([g["name"] for g in self.plan("shared_services and not nexus")], ["other"])
        self.assertEqual([g["name"] for g in self.plan("nexus")], ["nexus"])
        for selector in ("", "missing", "shared_services and ("):
            with self.subTest(selector=selector):
                self.output.unlink(missing_ok=True)
                result = self.invoke("--plan", extra={"E2E_SELECTOR": selector})
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.output.exists())

    def test_extra_nexus_cases_cannot_share_the_same_job_budget(self):
        with (self.folder / "test_cases.py").open("a") as source:
            source.write("\n@pytest.mark.nexus\ndef test_more_nexus():\n    pass\n")
        result = self.invoke("--plan", extra={"E2E_SELECTOR": "nexus"})
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("exactly one case", result.stderr)
        self.assertFalse(self.output.exists())

    def test_each_job_executes_only_its_cases_with_separate_reports(self):
        for group in self.plan():
            result = self.run_group(group, extra={"PYTEST_ADDOPTS": "-k missing", "E2E_TESTS_NUMBER_PROCESSES": "2"})
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((self.folder / f"{group['name']}-ran").exists())
            self.assertTrue((self.folder / f"pytest_e2e_{group['name']}.xml").exists())
            if group["name"] == "other":
                self.assertFalse((self.folder / "nexus-ran").exists())

    def test_nexus_cannot_be_hidden_in_the_other_job_including_xdist(self):
        group = self.plan()[1]
        group["name"] = "other"
        for processes in ("1", "2"):
            with self.subTest(processes=processes):
                result = self.run_group(group, extra={"E2E_TESTS_NUMBER_PROCESSES": processes})
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("Nexus must run separately", result.stdout + result.stderr)
                self.assertFalse((self.folder / "nexus-ran").exists())

    def test_stale_empty_and_malformed_requests_fail_before_execution(self):
        original = self.plan()[0]
        invalid = [
            None,
            {},
            {**original, "checkout_sha": "0" * 40},
            {**original, "tests": []},
            {**original, "tests": ["--help"]},
            {**original, "tests": ["../test_cases.py::test_other"]},
            {**original, "tests": original["tests"] * 2},
        ]
        for group in invalid:
            with self.subTest(group=group):
                result = self.run_group(group)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertFalse((self.folder / "other-ran").exists())

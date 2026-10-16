"""Check the main workflow's selectors against real E2E collection."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class MainTestSelectionTests(unittest.TestCase):
    def collect_groups(self, selector):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "groups"
            env = dict(
                os.environ,
                PYTHONPATH=os.pathsep.join((str(ROOT), str(ROOT / "e2e_tests"))),
                E2E_SELECTOR=selector,
                GITHUB_OUTPUT=str(output),
            )
            env.pop("PYTEST_ADDOPTS", None)
            result = subprocess.run(
                [sys.executable, "ci_groups.py", "--plan"],
                cwd=ROOT / "e2e_tests",
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return {group["name"]: set(group["tests"]) for group in json.loads(output.read_text().split("groups=")[-1])}

    def test_no_consent_excludes_only_nexus_dependencies(self):
        workflow = (ROOT / ".github/workflows/deploy_tre.yml").read_text()
        expression = workflow.split("e2eTestsCustomSelector: >-", 1)[1].split("acceptNexusEula:", 1)[0]
        selectors = [value for value in re.findall(r"'([^']*)'", expression) if "extended" in value]
        self.assertEqual(len(selectors), 3)
        push, consent, no_consent = [self.collect_groups(selector) for selector in selectors]
        review_vm = "test_airlock.py::test_airlock_review_vm_flow"
        self.assertEqual(set(no_consent), {"other"})
        self.assertEqual(set(consent), {"other", "nexus"})
        self.assertEqual(len(consent["nexus"]), 1)
        self.assertEqual(consent["other"] - no_consent["other"], {review_vm})
        self.assertEqual(no_consent["other"] - consent["other"], set())
        self.assertIn("test_airlock.py::test_draft_container_is_deleted_after_submit", no_consent["other"])
        self.assertIn("test_airlock_consolidated.py::test_v2_export_uses_workspace_storage", no_consent["other"])
        self.assertLess(push["other"], no_consent["other"])
        self.assertFalse(any(node.startswith("test_airlock") for node in push["other"]))

"""Keep CI deployments stable within a region and separate across locations."""

from pathlib import Path
import subprocess
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from ci_environment_id import environment_id  # noqa: E402


class EnvironmentTests(unittest.TestCase):
    def test_observed_cross_region_conflict_gets_distinct_names(self):
        ref = "refs/pull/5092/merge"
        self.assertEqual(environment_id(ref, "switzerlandnorth"), "e06583c4")
        self.assertEqual(environment_id(ref, "swedencentral"), "637595c5")
        self.assertNotIn("a66984da", (environment_id(ref, "switzerlandnorth"), environment_id(ref, "swedencentral")))

    def test_same_region_reruns_keep_the_backend_and_vault_names(self):
        first = environment_id("refs/pull/5092/merge", "switzerlandnorth")
        self.assertEqual(first, environment_id("refs/pull/5092/merge", "Switzerland North", "AZURECLOUD"))

    def test_refs_and_clouds_have_separate_environments(self):
        cases = [
            ("refs/pull/5092/merge", "AzureCloud"),
            ("refs/pull/5106/merge", "AzureCloud"),
            ("refs/heads/fix/keyvault", "AzureCloud"),
            ("refs/pull/5092/merge", "AzureUSGovernment"),
        ]
        self.assertEqual(len({environment_id(ref, "switzerlandnorth", cloud) for ref, cloud in cases}), len(cases))

    def test_invalid_or_production_contexts_fail(self):
        for ref in (
            "",
            "refs/heads/main",
            "refs/pull/0/merge",
            "refs/pull/1/head",
            "refs/heads/a\nb",
            "refs/heads/a b",
            "refs/heads/a..b",
            "refs/heads/.hidden",
            "refs/heads/a.lock",
            "refs/heads/a/",
        ):
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                environment_id(ref, "switzerlandnorth")
        for location in ("", "north/europe", "Switzerland\tNorth", "west-europe"):
            with self.subTest(location=location), self.assertRaises(ValueError):
                environment_id("refs/pull/5092/merge", location)
        with self.assertRaises(ValueError):
            environment_id("refs/pull/5092/merge", "switzerlandnorth", "unknown-cloud")

    def test_workflow_cli_returns_only_the_environment_id(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "ci_environment_id.py"),
                "--ref",
                "refs/pull/5092/merge",
                "--location",
                "switzerlandnorth",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(result.stdout, "e06583c4\n")


if __name__ == "__main__":
    unittest.main()

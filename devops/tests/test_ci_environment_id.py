"""Keep CI deployments stable within a region and separate across locations."""

import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from ci_environment_id import environment_id, environment_prefix, repository_owns  # noqa: E402


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

    def run_cli(self, *args, prefix=None):
        env = {key: value for key, value in os.environ.items() if key not in ("CI_ENV_PREFIX", "GITHUB_REPOSITORY")}
        if prefix is not None:
            env["CI_ENV_PREFIX"] = prefix
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "ci_environment_id.py"), *args],
            capture_output=True,
            text=True,
            env=env,
        )

    def test_workflow_cli_adds_the_prefix_only_when_asked(self):
        args = ("--ref", "refs/pull/5092/merge", "--location", "switzerlandnorth")
        self.assertEqual(self.run_cli(*args, "--with-prefix").stdout, "tree06583c4\n")
        self.assertEqual(self.run_cli(*args, "--with-prefix", prefix="").stdout, "tree06583c4\n")
        self.assertEqual(self.run_cli(*args, "--with-prefix", prefix="frk").stdout, "frke06583c4\n")
        self.assertEqual(self.run_cli(*args, prefix="frk").stdout, "e06583c4\n")
        self.assertNotEqual(self.run_cli(*args, "--with-prefix", prefix="frktre").returncode, 0)


class PrefixTests(unittest.TestCase):
    def test_default_prefix_keeps_upstream_names(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(environment_prefix(), "tre")
        with patch.dict(os.environ, {"CI_ENV_PREFIX": "", "GITHUB_REPOSITORY": "microsoft/AzureTRE"}):
            self.assertEqual(environment_prefix(), "tre")

    def test_fork_must_set_the_prefix_explicitly(self):
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "contoso/AzureTRE", "CI_ENV_PREFIX": ""}):
            with self.assertRaises(ValueError):
                environment_prefix()
            self.assertEqual(environment_prefix("frk"), "frk")
            # A fork with its own subscription keeps the upstream names on purpose.
            self.assertEqual(environment_prefix("tre"), "tre")
        for repository in ("microsoft/AzureTRE", "Microsoft/azuretre", ""):
            with (
                self.subTest(repository=repository),
                patch.dict(os.environ, {"GITHUB_REPOSITORY": repository, "CI_ENV_PREFIX": ""}),
            ):
                self.assertEqual(environment_prefix(), "tre")

    def test_fork_prefix_fills_the_tre_id_limit(self):
        self.assertEqual(environment_prefix("frk"), "frk")
        self.assertEqual(len(environment_prefix("frk") + environment_id("refs/pull/1/merge", "uksouth")), 11)

    def test_invalid_prefixes_fail(self):
        # Longer prefixes break the 11-character tre_id limit. Azure storage names need lowercase.
        for prefix in ("frktre", "fr", "FRK", "1fr", "fr-", "fr_", "f k"):
            with self.subTest(prefix=prefix), self.assertRaises(ValueError):
                environment_prefix(prefix)


class RepositoryOwnershipTests(unittest.TestCase):
    def test_untagged_groups_belong_to_upstream_or_another_prefix(self):
        for tags in (None, {}, {"ci_git_ref": "refs/pull/1/merge"}):
            with self.subTest(tags=tags):
                self.assertTrue(repository_owns(tags, "microsoft/AzureTRE", "tre"))
                self.assertTrue(repository_owns(tags, "contoso/AzureTRE", "frk"))
                # A fork with the default prefix cannot tell its old groups from upstream groups.
                self.assertFalse(repository_owns(tags, "contoso/AzureTRE", "tre"))
                self.assertFalse(repository_owns(tags, "", "tre"))

    def test_only_the_tagged_repository_owns_the_group(self):
        tags = {"ci_git_ref": "refs/pull/1/merge", "ci_repository": "contoso/AzureTRE"}
        # A tag decides ownership whatever the prefix is.
        self.assertTrue(repository_owns(tags, "contoso/AzureTRE"))
        self.assertTrue(repository_owns(tags, "CONTOSO/azuretre"))
        self.assertFalse(repository_owns(tags, "microsoft/AzureTRE"))
        self.assertFalse(repository_owns(tags, ""))
        self.assertFalse(repository_owns({"ci_repository": 3}, "contoso/AzureTRE"))


if __name__ == "__main__":
    unittest.main()

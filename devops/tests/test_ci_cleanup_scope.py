"""Verify cleanup ownership, pagination and the shared workflow lock contract."""

from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("ci_cleanup_scope", SCRIPTS / "ci_cleanup_scope.py")
scope = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scope)


class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(
            os.environ,
            {
                "GITHUB_ACTIONS": "true",
                "GITHUB_REPOSITORY": "microsoft/AzureTRE",
                "GITHUB_RUN_ID": "123",
                "GITHUB_RUN_ATTEMPT": "2",
                "CI_CLEANUP_REF": "refs/pull/51/merge",
                "AZURE_SUBSCRIPTION_ID": "sub",
            },
            clear=True,
        )
        self.env.start()
        self.addCleanup(self.env.stop)
        self.ctx = scope.context()
        self.run = {
            "id": 123,
            "run_attempt": 2,
            "status": "in_progress",
            "path": ".github/workflows/clean_validation_envs.yml",
            "repository": {"full_name": "microsoft/AzureTRE"},
        }
        self.jobs = [{"id": 10, "name": "Clean refs/pull/51/merge", "status": "in_progress"}]
        self.requests = []

    def github(self, ctx, suffix):
        self.requests.append(suffix)
        if suffix == "/actions/runs/123":
            return deepcopy(self.run)
        self.assertIn("/attempts/2/jobs?", suffix)
        page = int(suffix.split("page=")[-1])
        return {"total_count": len(self.jobs), "jobs": deepcopy(self.jobs[(page - 1) * 100 : page * 100])}

    def test_current_job_identity_selects_the_reference_lock(self):
        with patch.object(scope, "github", side_effect=self.github), patch.object(scope, "verify_concurrency") as lock:
            scope.verify_lock(self.ctx)
        lock.assert_called_once_with(self.ctx, job_id=10)

    def test_later_page_job_is_found(self):
        self.jobs = [{"id": i, "name": "Other " + str(i), "status": "completed"} for i in range(100, 200)] + self.jobs
        with patch.object(scope, "github", side_effect=self.github), patch.object(scope, "verify_concurrency") as lock:
            scope.verify_lock(self.ctx)
        lock.assert_called_once_with(self.ctx, job_id=10)
        self.assertTrue(any(suffix.endswith("page=2") for suffix in self.requests))

    def test_run_pending_behind_another_reference_still_verifies_this_job(self):
        # Observed live: run 37544274766 was pending while another matrix job waited.
        self.run["status"] = "pending"
        self.jobs.append({"id": 11, "name": "Clean refs/pull/4904/merge", "status": "pending"})
        with patch.object(scope, "github", side_effect=self.github), patch.object(scope, "verify_concurrency") as lock:
            scope.verify_lock(self.ctx)
        lock.assert_called_once_with(self.ctx, job_id=10)

    def test_stale_attempt_completed_foreign_or_wrong_workflow_is_refused(self):
        for key, value in (
            ("id", 999),
            ("run_attempt", 1),
            ("status", "completed"),
            ("path", ".github/workflows/other.yml"),
            ("repository", {"full_name": "other/repo"}),
        ):
            before = self.run[key]
            self.run[key] = value
            with (
                self.subTest(key=key),
                patch.object(scope, "github", side_effect=self.github),
                self.assertRaises(scope.RecoveryError),
            ):
                scope.verify_lock(self.ctx)
            self.run[key] = before

    def test_missing_ambiguous_or_pending_job_is_refused(self):
        original = deepcopy(self.jobs)
        for jobs in ([], original * 2, [{**original[0], "status": "queued"}], [original[0], {**original[0], "id": 11}]):
            self.jobs = jobs
            with (
                self.subTest(jobs=jobs),
                patch.object(scope, "github", side_effect=self.github),
                self.assertRaises(scope.RecoveryError),
            ):
                scope.verify_lock(self.ctx)

    def test_incomplete_or_inconsistent_pages_are_refused(self):
        for data in (
            {},
            {"total_count": 1001, "jobs": []},
            {"total_count": True, "jobs": []},
            {"total_count": 2, "jobs": self.jobs},
            {"total_count": 0, "jobs": self.jobs},
        ):
            with patch.object(scope, "github", side_effect=[self.run, data]), self.assertRaises(scope.RecoveryError):
                scope.verify_lock(self.ctx)

    def test_rate_limit_or_lock_failure_never_allows_cleanup(self):
        with (
            patch.object(scope, "github", side_effect=scope.RecoveryError("rate limit")),
            self.assertRaises(scope.RecoveryError),
        ):
            scope.verify_lock(self.ctx)
        with (
            patch.object(scope, "github", side_effect=self.github),
            patch.object(scope, "verify_concurrency", side_effect=scope.RecoveryError("no owner")),
        ):
            with self.assertRaises(scope.RecoveryError):
                scope.verify_lock(self.ctx)

    def test_unscoped_non_ci_and_invalid_references_are_refused(self):
        for key, value in (
            ("CI_CLEANUP_REF", ""),
            ("CI_CLEANUP_REF", "refs/heads/../other"),
            ("GITHUB_RUN_ID", ""),
            ("GITHUB_RUN_ATTEMPT", "0"),
            ("GITHUB_ACTIONS", "false"),
        ):
            with patch.dict(os.environ, {key: value}), self.assertRaises((scope.RecoveryError, ValueError)):
                scope.context()

    def test_plan_deduplicates_regions_and_includes_main_separately(self):
        groups = {
            "rg-treaaaa1111": "refs/pull/51/merge",
            "rg-treaaaa1111-mgmt": "refs/pull/51/merge",
            "rg-trebbbb2222-mgmt": "refs/pull/51/merge",
            "rg-trecccc3333": "refs/heads/feature/test",
            "rg-trelegacy-mgmt": None,
            "production": "refs/heads/production",
        }
        self.assertEqual(scope.references(groups), ["refs/heads/feature/test", "refs/heads/main", "refs/pull/51/merge"])
        self.assertEqual(scope.references({}), ["refs/heads/main"])

    def test_plan_rejects_invalid_refs_and_matrix_overflow(self):
        for groups in (
            {"rg-trex": 123},
            {"rg-trex": "refs/heads/../bad"},
            {f"rg-tre{i}": f"refs/pull/{i + 1}/merge" for i in range(256)},
        ):
            with self.assertRaises((scope.RecoveryError, ValueError)):
                scope.references(groups)

    def test_target_requires_consistent_pair_ownership(self):
        ref = self.ctx["ref"]
        scope.verify_target({"rg-treaaaa1111-mgmt": ref}, ref, "rg-treaaaa1111-mgmt")
        scope.verify_target({"rg-treaaaa1111": ref, "rg-treaaaa1111-mgmt": ref}, ref, "rg-treaaaa1111")
        for groups in (
            {},
            {"rg-treaaaa1111": None, "rg-treaaaa1111-mgmt": ref},
            {"rg-treaaaa1111": "refs/pull/99/merge", "rg-treaaaa1111-mgmt": ref},
        ):
            with self.assertRaises(scope.RecoveryError):
                scope.verify_target(groups, ref, "rg-treaaaa1111-mgmt")
        with self.assertRaises(scope.RecoveryError):
            scope.verify_target({"rg-treaaaa1111": "refs/heads/main"}, "refs/heads/main", "rg-treaaaa1111")

    def test_inventory_verifies_subscription_and_resource_ids(self):
        group = {
            "name": "rg-treaaaa1111",
            "id": "/subscriptions/sub/resourceGroups/rg-treaaaa1111",
            "tags": {"ci_git_ref": self.ctx["ref"]},
        }
        with patch.object(
            scope.subprocess, "check_output", side_effect=[json.dumps({"id": "sub"}), json.dumps([group])]
        ):
            self.assertEqual(scope.inventory(), {"rg-treaaaa1111": self.ctx["ref"]})
        for groups in (
            None,
            [group, group],
            [{**group, "id": "/subscriptions/other/resourceGroups/rg-treaaaa1111"}],
            [{**group, "tags": "bad"}],
        ):
            with patch.object(
                scope.subprocess, "check_output", side_effect=[json.dumps({"id": "sub"}), json.dumps(groups)]
            ):
                with self.assertRaises(scope.RecoveryError):
                    scope.inventory()
        with (
            patch.object(scope.subprocess, "check_output", return_value=json.dumps({"id": "other"})),
            self.assertRaises(scope.RecoveryError),
        ):
            scope.inventory()


class WorkflowContractTests(unittest.TestCase):
    def test_all_supported_writers_share_the_reference_group(self):
        workflows = SCRIPTS.parents[1] / ".github/workflows"
        deploy = (workflows / "deploy_tre_reusable.yml").read_text()
        self.assertIn('concurrency: "deploy-${{ inputs.ciGitRef }}"', deploy)
        self.assertIn("CI_GIT_REF: ${{ inputs.ciGitRef }}", deploy)
        explicit = (workflows / "pr_comment_bot.yml").read_text()
        for name in ("ciGitRef", "branchCiGitRef"):
            self.assertIn("group: deploy-${{ needs.pr_comment.outputs." + name + " }}", explicit)
        scheduled = (workflows / "clean_validation_envs.yml").read_text()
        self.assertIn("group: deploy-${{ matrix.ref }}", scheduled)
        self.assertIn("CI_CLEANUP_REF: ${{ matrix.ref }}", scheduled)
        self.assertIn("needs: plan", scheduled)
        self.assertIn("ref: ${{ fromJSON(needs.plan.outputs.refs) }}", scheduled)
        self.assertNotRegex(deploy + explicit + scheduled, r"cancel-in-progress:\s*true")

    def test_cleanup_waits_until_all_resource_group_deletions_complete(self):
        script = (SCRIPTS / "clean_ci_validation_envs.sh").read_text()
        self.assertNotIn("--no-wait", script)
        self.assertNotIn("actions/runs?", script)
        self.assertLess(script.index("ci_cleanup_scope.py verify-lock"), script.index("az group list"))
        self.assertRegex(script, re.compile(r"function destroyEnv.*?verify-target.*?destroy_env_no_terraform", re.S))

    def test_cleanup_job_keeps_the_lock_for_long_deletions(self):
        scheduled = (SCRIPTS.parents[1] / ".github/workflows/clean_validation_envs.yml").read_text()
        clean = scheduled[scheduled.index("\n  clean:\n") : scheduled.index("\n  validate:\n")]
        # Explicit destruction uses the GitHub-hosted default of 360 minutes.
        self.assertRegex(clean, r"\n    timeout-minutes: 360\n")

    def test_recovery_token_reaches_only_the_pr_bootstrap_command(self):
        root = SCRIPTS.parents[1]
        deploy = (root / ".github/workflows/deploy_tre_reusable.yml").read_text()
        management = deploy[deploy.index("\n  deploy_management:\n") :]
        management = management[: management.index("\n    steps:\n")]
        self.assertRegex(management, r"\n      actions: read")
        # A reusable workflow cannot elevate the caller's token permissions.
        for name in ("pr_comment_bot.yml", "deploy_tre.yml", "deploy_tre_branch.yml"):
            caller = (root / ".github/workflows" / name).read_text()
            block = caller[caller.index("uses: ./.github/workflows/deploy_tre_reusable.yml") :]
            block = block[: block.index("\n    with:\n")]
            with self.subTest(caller=name):
                self.assertRegex(block, r"\n      actions: read")
        action = (root / ".github/actions/devcontainer_run_command/action.yml").read_text()
        self.assertRegex(
            action,
            re.compile(
                r"CI_RECOVERY_GITHUB_TOKEN: >-\s+\$\{\{ github\.event_name == 'issue_comment' && "
                r"startsWith\(inputs\.CI_GIT_REF, 'refs/pull/'\)\s+&& contains\(inputs\.COMMAND, 'make bootstrap'\) "
                r"&& github\.token \|\| '' \}\}"
            ),
        )
        self.assertIn("-e CI_RECOVERY_GITHUB_TOKEN \\", action)
        self.assertNotRegex(action, r"-e GITHUB_TOKEN\b")


if __name__ == "__main__":
    unittest.main()

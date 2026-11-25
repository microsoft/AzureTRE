"""Check delegated deployment ownership against GitHub run and queue responses."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "devops/scripts"))
import recover_bootstrap_lease as recovery  # noqa: E402
import verify_deployment_lock as guard  # noqa: E402


class DelegatedLockTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(
            os.environ,
            {
                "CI_DEPLOYMENT_LOCK_DELEGATED": "true",
                "CI_GIT_REF": "refs/heads/feature/test",
                "GITHUB_ACTIONS": "true",
                "GITHUB_REF": "refs/heads/feature/test",
                "GITHUB_REPOSITORY": "microsoft/AzureTRE",
                "GITHUB_RUN_ID": "123",
                "GITHUB_RUN_ATTEMPT": "2",
                "GITHUB_SHA": "a" * 40,
            },
            clear=True,
        )
        self.env.start()
        self.addCleanup(self.env.stop)
        self.ctx = guard.context()
        self.run = {
            "id": 123,
            "run_attempt": 2,
            "status": "in_progress",
            "event": "workflow_dispatch",
            "path": ".github/workflows/deploy_tre_branch.yml",
            "head_branch": "feature/test",
            "head_sha": "a" * 40,
            "repository": {"full_name": "microsoft/AzureTRE"},
            "head_repository": {"full_name": "microsoft/AzureTRE"},
        }
        self.group = {
            "group_name": "deploy-refs/heads/feature/test",
            "total_count": 1,
            "group_members": [{"run_id": 123, "status": "in_progress"}],
        }
        self.requests = []
        for module in (guard, recovery):
            mock = patch.object(module, "github", side_effect=self.github)
            mock.start()
            self.addCleanup(mock.stop)

    def github(self, ctx, suffix):
        self.assertEqual(ctx, self.ctx)
        self.requests.append(suffix)
        if suffix == "/actions/runs/123":
            return deepcopy(self.run)
        if suffix == "/actions/concurrency_groups/deploy-refs%2Fheads%2Ffeature%2Ftest":
            return deepcopy(self.group)
        if suffix == "/actions/jobs/456":
            return {
                "id": 456,
                "run_id": 123,
                "run_attempt": 2,
                "status": "in_progress",
                "name": "Deploy PR / Deploy Management",
            }
        self.fail(f"Unexpected GitHub request: {suffix}")

    def test_current_branch_workflow_owner_is_accepted_with_waiting_cleanup(self):
        self.group["group_members"].append({"run_id": 999, "job_id": 101, "status": "pending"})
        self.group["total_count"] = 2
        guard.verify_delegated_lock(self.ctx)
        self.assertEqual(len(self.requests), 2)

    def test_active_parent_run_status_uses_the_canonical_in_progress_owner(self):
        for status in ("queued", "pending", "waiting", "requested"):
            self.run["status"] = status
            with self.subTest(status=status):
                guard.verify_delegated_lock(self.ctx)

    def test_wrong_run_attempt_source_or_repository_is_refused(self):
        for key, value in (
            ("id", 456),
            ("id", True),
            ("run_attempt", 1),
            ("run_attempt", "2"),
            ("status", "unknown"),
            ("status", "completed"),
            ("event", "issue_comment"),
            ("path", ".github/workflows/pr_comment_bot.yml"),
            ("head_branch", "another-branch"),
            ("head_sha", "b" * 40),
            ("repository", {"full_name": "another/repo"}),
            ("head_repository", {"full_name": "another/repo"}),
        ):
            before = self.run[key]
            self.run[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(guard.RecoveryError):
                guard.verify_delegated_lock(self.ctx)
            self.run[key] = before

    def test_wrong_pending_missing_or_ambiguous_owner_is_refused(self):
        for members in (
            [],
            [{"run_id": 999, "status": "in_progress"}],
            [{"run_id": 123, "status": "pending"}],
            [{"run_id": 123, "status": "in_progress"}, {"run_id": 999, "status": "in_progress"}],
        ):
            self.group["group_members"] = members
            self.group["total_count"] = len(members)
            with self.subTest(members=members), self.assertRaises(guard.RecoveryError):
                guard.verify_delegated_lock(self.ctx)

    def test_management_job_lease_cannot_substitute_for_caller_workflow_lease(self):
        # The existing bootstrap verifier accepts this job owner. Delegation must
        # reject it because it does not protect branch preparation.
        self.group["group_members"][0]["job_id"] = 456
        with self.assertRaisesRegex(guard.RecoveryError, "workflow-level"):
            guard.verify_delegated_lock(self.ctx)
        self.assertIn("/actions/jobs/456", self.requests)

    def test_wrong_group_or_incomplete_queue_is_refused(self):
        for key, value in (("group_name", "deploy-other"), ("total_count", 2)):
            before = self.group[key]
            self.group[key] = value
            with self.subTest(key=key), self.assertRaises(guard.RecoveryError):
                guard.verify_delegated_lock(self.ctx)
            self.group[key] = before

    def test_invalid_context_is_refused_before_any_request(self):
        for key, value in (
            ("GITHUB_ACTIONS", "false"),
            ("CI_GIT_REF", "refs/pull/123/merge"),
            ("CI_GIT_REF", "refs/heads/main"),
            ("CI_GIT_REF", "refs/heads/another"),
            ("GITHUB_REF", "refs/heads/another"),
            ("GITHUB_REPOSITORY", "../another/repo"),
            ("GITHUB_RUN_ID", ""),
            ("GITHUB_RUN_ATTEMPT", "0"),
            ("GITHUB_SHA", "missing"),
        ):
            with (
                self.subTest(key=key),
                patch.dict(os.environ, {key: value}),
                self.assertRaises((guard.RecoveryError, ValueError)),
            ):
                guard.context()
        self.assertEqual(self.requests, [])

    def test_other_callers_keep_the_reusable_lock_without_delegation_checks(self):
        output = io.StringIO()
        with patch.dict(os.environ, {"CI_DEPLOYMENT_LOCK_DELEGATED": "false"}), redirect_stdout(output):
            self.assertEqual(guard.main(), 0)
        self.assertEqual(self.requests, [])
        self.assertIn("reusable workflow holds", output.getvalue())

    def test_invalid_delegation_flag_and_api_failure_fail_the_command(self):
        for value in ("", "yes", "TRUE"):
            with patch.dict(os.environ, {"CI_DEPLOYMENT_LOCK_DELEGATED": value}), redirect_stderr(io.StringIO()):
                self.assertEqual(guard.main(), 1)
        output, error = io.StringIO(), io.StringIO()
        with (
            patch.object(recovery, "github", side_effect=guard.RecoveryError("API unavailable")),
            redirect_stdout(output),
            redirect_stderr(error),
        ):
            self.assertEqual(guard.main(), 1)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("API unavailable", error.getvalue())


if __name__ == "__main__":
    unittest.main()

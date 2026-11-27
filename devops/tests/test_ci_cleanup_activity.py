"""Protect recently used environments without retaining unrelated or orphaned groups."""

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import ci_cleanup_activity as activity  # noqa: E402


class ActivityTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 11, 12, tzinfo=timezone.utc).timestamp()
        self.ctx = {"repository": "microsoft/AzureTRE", "ref": "refs/heads/feature/test", "run_id": 123}
        self.members = [{"run_id": 123, "job_id": 10, "status": "in_progress"}]
        self.runs = []
        self.requests = []

    def run_record(self, number=200, age_hours=1, **kwargs):
        return {
            "id": number,
            "path": activity.BRANCH_WORKFLOW,
            "event": "workflow_dispatch",
            "head_branch": "feature/test",
            "head_sha": "a" * 40,
            "repository": {"full_name": self.ctx["repository"]},
            "head_repository": {"full_name": self.ctx["repository"]},
            "status": "completed",
            "conclusion": "success",
            "created_at": "2026-09-01T00:00:00Z",
            "updated_at": datetime.fromtimestamp(self.now - age_hours * 3600, timezone.utc).isoformat(),
            **kwargs,
        }

    def github(self, ctx, suffix):
        self.requests.append(suffix)
        self.assertEqual(ctx, self.ctx)
        self.assertTrue(suffix.startswith("/actions/workflows/deploy_tre_branch.yml/runs?"))
        query = parse_qs(urlsplit(suffix).query)
        self.assertEqual(query["branch"], ["feature/test"])
        self.assertEqual(query["event"], ["workflow_dispatch"])
        self.assertNotIn("created", query)  # Older runs can have a recent rerun.
        page = int(query["page"][0])
        return {"total_count": len(self.runs), "workflow_runs": deepcopy(self.runs[(page - 1) * 100 : page * 100])}  # noqa: E203

    def allowed(self, age=100, threshold=4):
        with patch.object(activity, "github", side_effect=self.github):
            return activity.mutation_allowed(self.ctx, self.members, int(self.now - age * 3600), threshold, self.now)

    def test_old_commit_and_recent_success_failure_or_cancellation_are_retained(self):
        for conclusion in ("success", "failure", "cancelled", "timed_out"):
            with self.subTest(conclusion=conclusion):
                self.runs = [self.run_record(conclusion=conclusion, age_hours=1 / 60)]
                self.assertFalse(self.allowed())

    def test_recent_rerun_of_old_sha_extends_activity(self):
        self.runs = [self.run_record(run_attempt=4, head_sha="b" * 40)]
        self.assertFalse(self.allowed())

    def test_preparation_and_pending_runs_are_active_without_queue_membership(self):
        for status in activity.ACTIVE_STATUSES:
            with self.subTest(status=status):
                self.runs = [self.run_record(status=status, age_hours=100)]
                self.assertFalse(self.allowed())

    def test_old_activity_preserves_thresholds_and_new_commits_extend_activity(self):
        self.runs = [self.run_record(age_hours=6)]
        self.assertTrue(self.allowed(threshold=4))
        self.assertFalse(self.allowed(threshold=48))
        self.assertFalse(self.allowed(age=1))
        self.runs = [self.run_record(age_hours=60)]
        self.assertTrue(self.allowed(threshold=48))
        self.runs = []
        self.assertTrue(self.allowed(threshold=48))

    def test_second_page_recent_run_prevents_destruction(self):
        self.runs = [self.run_record(number=n, age_hours=100) for n in range(200, 300)] + [self.run_record(number=300)]
        self.assertFalse(self.allowed(threshold=48))
        self.assertTrue(self.requests[-1].endswith("page=2"))

    def test_unrelated_history_is_not_requested(self):
        self.runs = []
        self.assertTrue(self.allowed())
        self.assertEqual(len(self.requests), 1)
        self.assertIn("branch=feature%2Ftest", self.requests[0])

    def test_unexpected_identity_status_or_time_refuses_cleanup(self):
        for change in (
            {"id": True},
            {"path": activity.CLEANUP_WORKFLOW},
            {"event": "issue_comment"},
            {"head_branch": "other"},
            {"repository": {"full_name": "other/repo"}},
            {"head_repository": None},
            {"status": "unknown"},
            {"updated_at": None},
            {"updated_at": "not-a-date"},
            {"updated_at": "2026-10-11T11:00:00"},
            {"updated_at": "2026-10-12T11:00:00Z"},
            {"updated_at": "2026-08-01T11:00:00Z"},
        ):
            with self.subTest(change=change), self.assertRaises(activity.RecoveryError):
                self.runs = [self.run_record(age_hours=100, **change)]
                self.allowed()

    def test_incomplete_duplicate_or_unbounded_history_refuses_cleanup(self):
        for response in (
            {},
            {"total_count": 1001, "workflow_runs": []},
            {"total_count": True, "workflow_runs": []},
            {"total_count": 2, "workflow_runs": [self.run_record(age_hours=100)]},
            {"total_count": 2, "workflow_runs": [self.run_record(age_hours=100)] * 2},
            {"total_count": 0, "workflow_runs": [self.run_record(age_hours=100)]},
        ):
            with (
                self.subTest(response=response),
                patch.object(activity, "github", return_value=response),
                self.assertRaises(activity.RecoveryError),
            ):
                activity.mutation_allowed(self.ctx, self.members, int(self.now - 100 * 3600), 4, self.now)

    def test_changed_page_count_and_api_error_refuse_cleanup(self):
        first = {
            "total_count": 101,
            "workflow_runs": [self.run_record(number=n, age_hours=100) for n in range(200, 300)],
        }
        for responses in ([first, {"total_count": 102, "workflow_runs": []}], activity.RecoveryError("rate limit")):
            with patch.object(activity, "github", side_effect=responses), self.assertRaises(activity.RecoveryError):
                activity.mutation_allowed(self.ctx, self.members, int(self.now - 100 * 3600), 4, self.now)

    def test_queued_deployment_or_unknown_work_defers_even_orphan_deletion(self):
        self.members.append({"run_id": 456, "status": "pending"})
        for path in (activity.BRANCH_WORKFLOW, ".github/workflows/pr_comment_bot.yml", None, activity.CLEANUP_WORKFLOW):
            run = {"id": 456, "path": path, "event": "schedule", "repository": {"full_name": self.ctx["repository"]}}
            with patch.object(activity, "github", return_value=run):
                self.assertFalse(activity.mutation_allowed(self.ctx, self.members))

    def test_verified_cleanup_successors_do_not_extend_activity(self):
        self.members.append({"run_id": 456, "job_id": 50, "status": "pending"})
        run = {
            "id": 456,
            "path": activity.CLEANUP_WORKFLOW,
            "event": "schedule",
            "run_attempt": 2,
            "repository": {"full_name": self.ctx["repository"]},
        }
        job = {"id": 50, "run_id": 456, "run_attempt": 2, "name": "Clean " + self.ctx["ref"], "status": "pending"}
        with patch.object(activity, "github", side_effect=[run, job]):
            self.assertTrue(activity.mutation_allowed(self.ctx, self.members))
        for change in ({"run_attempt": 1}, {"name": "Unidentified"}, {"id": 60}, {"status": "completed"}):
            with patch.object(activity, "github", side_effect=[run, {**job, **change}]):
                self.assertFalse(activity.mutation_allowed(self.ctx, self.members))

    def test_unverified_queue_identity_refuses_cleanup(self):
        self.members.append({"run_id": 456, "job_id": 50, "status": "pending"})
        with patch.object(activity, "github", return_value={}), self.assertRaises(activity.RecoveryError):
            activity.mutation_allowed(self.ctx, self.members)

    def test_orphan_decision_has_no_completed_run_grace_period(self):
        with patch.object(activity, "github") as github:
            self.assertTrue(activity.mutation_allowed(self.ctx, self.members))
            github.assert_not_called()

    def test_partial_or_invalid_age_requests_refuse_cleanup(self):
        for commit, hours in ((None, 4), (1, None), (-1, 4), (1, -1), (True, 4)):
            with self.subTest(commit=commit, hours=hours), self.assertRaises(activity.RecoveryError):
                activity.mutation_allowed(self.ctx, self.members, commit, hours, self.now)
        self.ctx["ref"] = "refs/pull/123/merge"
        with self.assertRaises(activity.RecoveryError):
            activity.mutation_allowed(self.ctx, self.members, int(self.now), 4, self.now)


if __name__ == "__main__":
    unittest.main()

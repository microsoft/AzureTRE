"""Check ownership, activity and state-preservation gates for PR lease recovery."""

from copy import deepcopy
import importlib.util
import hashlib
import io
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import urllib.error


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/recover_bootstrap_lease.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("recover_bootstrap_lease", SCRIPT)
recovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recovery)

ENV = {
    "CI_BOOTSTRAP_LEASE_RECOVERY": "true",
    "GITHUB_ACTIONS": "true",
    "CI_RECOVERY_PR_NUMBER": "5092",
    "GITHUB_REPOSITORY": "microsoft/AzureTRE",
    "GITHUB_RUN_ID": "123",
    "GITHUB_RUN_ATTEMPT": "1",
    "TF_VAR_ci_git_ref": "refs/pull/5092/merge",
    "TF_VAR_mgmt_resource_group_name": "rg-trea66984da-mgmt",
    "TF_VAR_mgmt_storage_account_name": "trea66984damgmt",
    "TF_VAR_terraform_state_container_name": "tfstate",
    "ARM_SUBSCRIPTION_ID": "test-subscription",
}
ORPHAN = {
    "name": "bootstrap.tfstate",
    "metadata": {},
    "properties": {
        "contentLength": 0,
        "blobType": "BlockBlob",
        "etag": '"test-etag"',
        "lastModified": "2026-10-05T08:35:23Z",
        "lease": {"duration": "infinite", "state": "leased", "status": "locked"},
    },
}


class RecoveryTests(unittest.TestCase):
    def test_regional_context_uses_the_matching_backend(self):
        regional = {
            "CI_ENVIRONMENT_ID": "e06583c4",
            "TF_VAR_location": "switzerlandnorth",
            "AZURE_ENVIRONMENT": "AzureCloud",
            "TF_VAR_mgmt_resource_group_name": "rg-tree06583c4-mgmt",
            "TF_VAR_mgmt_storage_account_name": "tree06583c4mgmt",
        }
        with patch.dict(os.environ, regional):
            self.assertEqual(recovery.context()["group"], "rg-tree06583c4-mgmt")
            self.assertEqual(recovery.context()["account"], "tree06583c4mgmt")

    def test_regional_context_refuses_foreign_regions_or_legacy_backend(self):
        cases = [
            {"CI_ENVIRONMENT_ID": "e06583c4", "TF_VAR_location": "swedencentral"},
            {"CI_ENVIRONMENT_ID": "e06583c4", "TF_VAR_location": "switzerlandnorth"},
            {"CI_ENVIRONMENT_ID": "637595c5", "TF_VAR_location": ""},
        ]
        for env in cases:
            with self.subTest(env=env), patch.dict(os.environ, env), self.assertRaises(recovery.RecoveryError):
                recovery.context()

    def setUp(self):
        self.env = patch.dict(os.environ, ENV, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.ctx = recovery.context()
        self.state = deepcopy(ORPHAN)
        self.calls = []
        self.activity = []
        self.exists = True
        self.group_tag = self.ctx["ref"]
        self.group_id = "/subscriptions/test-subscription/resourceGroups/rg-trea66984da-mgmt"
        self.account_id = self.group_id + "/providers/Microsoft.Storage/storageAccounts/trea66984damgmt"
        self.status_data = {}
        self.after_break = None
        self.break_error = None
        self.group_reads = 0
        self.change_on_second_group_read = None
        self.show_reads = 0
        self.change_on_second_show = None
        self.members = [{"run_id": 123, "status": "in_progress"}]
        self.current = {
            "head_sha": "a" * 40,
            "id": 123,
            "run_attempt": 1,
            "status": "in_progress",
            "event": "issue_comment",
            "path": ".github/workflows/pr_comment_bot.yml",
            "repository": {"full_name": "microsoft/AzureTRE"},
            "referenced_workflows": [
                {"path": "microsoft/AzureTRE/.github/workflows/deploy_tre_reusable.yml@" + "a" * 40, "sha": "a" * 40}
            ],
        }
        for name, implementation in (("azure", self.azure), ("github", self.github)):
            mock = patch.object(recovery, name, side_effect=implementation)
            mock.start()
            self.addCleanup(mock.stop)

    def azure(self, ctx, *args):
        self.calls.append(args)
        if args[:2] == ("group", "show"):
            self.group_reads += 1
            if self.group_reads == 2 and self.change_on_second_group_read:
                self.group_tag = self.change_on_second_group_read
            return {"id": self.group_id, "tags": {"ci_git_ref": self.group_tag}}
        if args[:3] == ("storage", "account", "show"):
            return {"id": self.account_id}
        self.assertEqual(args[:2], ("storage", "blob"))
        self.assertEqual(args[args.index("--auth-mode") + 1], "login")
        self.assertEqual(args[args.index("--account-name") + 1], "trea66984damgmt")
        self.assertEqual(args[args.index("--container-name") + 1], "tfstate")
        if args[2] == "exists":
            return {"exists": self.exists}
        if args[2] == "show":
            self.assertEqual(args[args.index("--name") + 1], "bootstrap.tfstate")
            self.show_reads += 1
            if self.show_reads == 2 and self.change_on_second_show:
                self.change_on_second_show(self.state)
            return deepcopy(self.state)
        self.assertEqual(args[2:4], ("lease", "break"))
        self.assertEqual(args[args.index("--blob-name") + 1], "bootstrap.tfstate")
        self.assertEqual(args[args.index("--lease-break-period") + 1], "0")
        self.assertEqual(args[args.index("--if-match") + 1], '"test-etag"')
        if self.break_error:
            raise self.break_error
        self.state["properties"]["lease"] = {"duration": None, "state": "broken", "status": "unlocked"}
        if self.after_break:
            self.after_break(self.state)
        return 0

    def github(self, ctx, suffix):
        self.activity.append(suffix)
        if suffix == "/actions/runs/123":
            return deepcopy(self.current)
        if suffix.startswith("/contents/"):
            content = (recovery.SOURCE / suffix.removeprefix("/contents/").split("?")[0]).read_bytes()
            return {
                "type": "file",
                "sha": hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest(),
            }
        if suffix.startswith("/actions/concurrency_groups/"):
            return {
                "group_name": "deploy-" + self.ctx["ref"],
                "total_count": len(self.members),
                "group_members": deepcopy(self.members),
            }
        status = suffix.split("status=")[1].split("&")[0]
        if status in self.status_data:
            value = self.status_data[status]
            if isinstance(value, Exception):
                raise value
            return deepcopy(value)
        runs = [{"id": 123}] if status == "in_progress" else []
        return {"total_count": len(runs), "workflow_runs": runs}

    def breaks(self):
        return [call for call in self.calls if call[:4] == ("storage", "blob", "lease", "break")]

    def assert_refused(self):
        with self.assertRaises(recovery.RecoveryError):
            recovery.recover(self.ctx)
        self.assertEqual(self.breaks(), [])

    def test_recovery_breaks_only_empty_bootstrap_lease_once_and_preserves_state(self):
        before = deepcopy(self.state)
        recovery.recover(self.ctx)
        self.assertEqual(len(self.breaks()), 1)
        self.assertEqual(recovery.snapshot(self.state), recovery.snapshot(before))
        self.assertEqual(self.calls[-1][2], "show")

    def test_missing_blob_needs_no_recovery_or_workflow_queries(self):
        self.exists = False
        recovery.recover(self.ctx)
        self.assertEqual(self.breaks(), [])
        self.assertEqual(self.activity, [])

    def test_unlocked_populated_state_is_not_touched(self):
        self.state["properties"]["contentLength"] = 12345
        self.state["properties"]["lease"] = {"status": "unlocked", "state": "available", "duration": None}
        recovery.recover(self.ctx)
        self.assertEqual(self.breaks(), [])
        self.assertEqual(self.activity, [])

    def test_non_ci_main_wrong_pr_and_wrong_backend_are_refused(self):
        for key, value in (
            ("CI_BOOTSTRAP_LEASE_RECOVERY", "false"),
            ("GITHUB_ACTIONS", "false"),
            ("TF_VAR_ci_git_ref", "refs/heads/main"),
            ("CI_RECOVERY_PR_NUMBER", "5005"),
            ("TF_VAR_mgmt_storage_account_name", "production"),
            ("TF_VAR_mgmt_resource_group_name", "production"),
            ("GITHUB_RUN_ID", ""),
            ("GITHUB_RUN_ATTEMPT", ""),
            ("ARM_SUBSCRIPTION_ID", ""),
            ("GITHUB_REPOSITORY", "../other"),
            ("TF_VAR_terraform_state_container_name", ""),
        ):
            with self.subTest(key=key), patch.dict(os.environ, {key: value}):
                with self.assertRaises(recovery.RecoveryError):
                    recovery.context()
        self.assertEqual(self.breaks(), [])

    def test_wrong_resource_group_identity_or_tag_is_refused(self):
        for key, value in (
            ("group_id", "/subscriptions/other/resourceGroups/rg-trea66984da-mgmt"),
            ("group_tag", "refs/pull/5005/merge"),
        ):
            with self.subTest(key=key):
                original = getattr(self, key)
                setattr(self, key, value)
                self.assert_refused()
                setattr(self, key, original)

    def test_wrong_storage_account_identity_is_refused(self):
        self.account_id += "other"
        self.assert_refused()

    def test_populated_state_and_any_lock_owner_are_refused(self):
        for update in (
            lambda value: value["properties"].update(contentLength=1),
            lambda value: value.update(metadata={"terraformlockid": "owner"}),
            lambda value: value.update(metadata={"TerraformLockId": "owner"}),
        ):
            self.state = deepcopy(ORPHAN)
            update(self.state)
            self.assert_refused()

    def test_finite_breaking_expired_and_unknown_leases_are_refused(self):
        for key, value in (("duration", "fixed"), ("state", "breaking"), ("state", "expired"), ("status", "unknown")):
            self.state = deepcopy(ORPHAN)
            self.state["properties"]["lease"][key] = value
            self.assert_refused()

    def test_incomplete_blob_data_is_refused(self):
        for update in (
            lambda value: value.update(name="devops.tfstate"),
            lambda value: value.pop("metadata"),
            lambda value: value["properties"].pop("etag"),
            lambda value: value["properties"].pop("lastModified"),
            lambda value: value["properties"].update(contentLength=False),
            lambda value: value["properties"].pop("lease"),
        ):
            self.state = deepcopy(ORPHAN)
            update(self.state)
            self.assert_refused()

    def test_unknown_workflows_block_recovery_in_every_active_status(self):
        for status in ("requested", "waiting", "pending", "queued", "in_progress"):
            self.status_data = {status: {"total_count": 1, "workflow_runs": [{"id": 999}]}}
            self.assert_refused()

    def test_unrelated_lint_does_not_block_eligible_recovery(self):
        self.status_data["in_progress"] = {
            "total_count": 2,
            "workflow_runs": [
                {"id": 123},
                {
                    "id": 999,
                    "path": ".github/workflows/build_validation_develop.yml",
                    "event": "pull_request",
                    "head_sha": "a" * 40,
                },
            ],
        }
        recovery.recover(self.ctx)
        self.assertEqual(len(self.breaks()), 1)

    def test_resource_processor_tests_do_not_block_eligible_recovery(self):
        self.status_data["queued"] = {
            "total_count": 1,
            "workflow_runs": [
                {
                    "id": 999,
                    "path": ".github/workflows/resource_processor_tests.yml",
                    "event": "pull_request",
                    "head_sha": "a" * 40,
                },
            ],
        }
        recovery.recover(self.ctx)
        self.assertEqual(len(self.breaks()), 1)

    def test_classified_workflows_exist(self):
        workflows = recovery.SOURCE / ".github/workflows"
        for name in recovery.READ_ONLY_WORKFLOWS | recovery.WRITER_WORKFLOWS:
            with self.subTest(name=name):
                self.assertTrue((workflows / name).is_file())

    def test_api_failure_and_rate_limit_refuse_recovery(self):
        self.status_data["queued"] = recovery.RecoveryError("GitHub API rate limit")
        self.assert_refused()

    def test_incomplete_api_activity_is_refused(self):
        for data in (
            {},
            {"total_count": 0, "workflow_runs": None},
            {"total_count": 1, "workflow_runs": []},
            {"total_count": 1001, "workflow_runs": []},
            {"total_count": 1, "workflow_runs": [{"id": "123"}]},
            {"total_count": 2, "workflow_runs": [{"id": 123}, {"id": 123}]},
        ):
            self.status_data = {"in_progress": data}
            self.assert_refused()

    def test_api_must_include_the_current_active_run(self):
        self.status_data["in_progress"] = {"total_count": 0, "workflow_runs": []}
        self.assert_refused()

    def test_completed_wrong_attempt_or_other_current_workflow_is_refused(self):
        for key, value in (
            ("status", "completed"),
            ("run_attempt", 2),
            ("event", "push"),
            ("path", ".github/workflows/other.yml"),
            ("repository", {"full_name": "other/repo"}),
            ("referenced_workflows", []),
        ):
            original = self.current[key]
            self.current[key] = value
            self.assert_refused()
            self.current[key] = original

    def test_owner_or_state_change_during_quiet_interval_refuses_recovery(self):
        self.change_on_second_group_read = "refs/pull/5005/merge"
        self.assert_refused()
        self.group_tag = self.ctx["ref"]
        self.group_reads = 0
        self.show_reads = 0
        self.state = deepcopy(ORPHAN)
        self.change_on_second_group_read = None
        self.change_on_second_show = lambda value: value["properties"].update(etag='"different"')
        self.assert_refused()

    def test_known_writers_and_github_managed_checks_do_not_block_the_lock_owner(self):
        cases = [
            {"path": "dynamic/agents/copilot-pull-request-reviewer", "event": "dynamic"},
            {"path": "dynamic/github-code-quality/codeql", "event": "dynamic"},
            {"path": "dynamic/github-code-scanning/codeql", "event": "dynamic"},
            {"path": "dynamic/pages/pages-build-deployment", "event": "dynamic"},
            {"path": ".github/workflows/deploy_tre_branch.yml", "head_sha": "a" * 40},
            {"path": ".github/workflows/pr_comment_bot.yml", "head_sha": "a" * 40},
            {"path": ".github/workflows/clean_validation_envs.yml", "head_sha": "a" * 40},
        ]
        for case in cases:
            for status in ("queued", "pending", "in_progress"):
                with self.subTest(case=case, status=status):
                    self.calls = []
                    self.state = deepcopy(ORPHAN)
                    runs = ([{"id": 123}] if status == "in_progress" else []) + [{"id": 999, **case}]
                    self.status_data = {status: {"total_count": len(runs), "workflow_runs": runs}}
                    recovery.recover(self.ctx)
                    self.assertEqual(len(self.breaks()), 1)

    def test_unknown_or_non_dynamic_github_managed_checks_block_recovery(self):
        cases = [
            {"path": "dynamic/pages/pages-build-deployment", "event": "push"},
            {"path": "dynamic/github-code-scanning/unknown", "event": "dynamic"},
        ]
        for case in cases:
            with self.subTest(case=case):
                self.status_data = {"queued": {"total_count": 1, "workflow_runs": [{"id": 999, **case}]}}
                self.assert_refused()

    def test_new_queued_writer_does_not_prevent_owner_progress(self):
        def enqueue(_):
            self.status_data["pending"] = {
                "total_count": 1,
                "workflow_runs": [
                    {"id": 999, "path": ".github/workflows/pr_comment_bot.yml", "head_sha": "a" * 40},
                ],
            }
            self.members.append({"run_id": 999, "status": "pending"})

        self.change_on_second_show = enqueue
        recovery.recover(self.ctx)
        self.assertEqual(len(self.breaks()), 1)

    def test_unknown_writer_starting_before_break_refuses_recovery(self):
        self.change_on_second_show = lambda _: self.status_data.update(
            queued={"total_count": 1, "workflow_runs": [{"id": 999}]}
        )
        self.assert_refused()

    def test_lost_concurrency_ownership_before_break_refuses_recovery(self):
        self.change_on_second_show = lambda _: self.members[0].update(run_id=999)
        self.assert_refused()

    def test_missing_ambiguous_or_pending_concurrency_owner_is_refused(self):
        for members in (
            [],
            [{"run_id": 123, "status": "pending"}],
            [{"run_id": 999, "status": "in_progress"}],
            [{"run_id": 123, "status": "in_progress"}] * 2,
        ):
            self.members = members
            self.assert_refused()

    def test_old_or_modified_workflow_source_refuses_recovery(self):
        original = self.github
        for path in ("clean_validation_envs.yml", "deploy_tre_reusable.yml", "pr_comment_bot.yml"):

            def source(ctx, suffix):
                if suffix.startswith("/contents/.github/workflows/" + path):
                    return {"type": "file", "sha": "b" * 40}
                return original(ctx, suffix)

            with self.subTest(path=path), patch.object(recovery, "github", side_effect=source):
                self.assert_refused()

    def test_pr_modified_allow_listed_workflow_cannot_classify_its_runs(self):
        original = self.github
        for path in ("build_validation_develop.yml", "deploy_tre_branch.yml"):

            def source(ctx, suffix):
                # The PR checkout and its run match each other, but differ from the trusted caller commit.
                if suffix == f"/contents/.github/workflows/{path}?ref={'a' * 40}":
                    return {"type": "file", "sha": "b" * 40}
                return original(ctx, suffix)

            run = {"id": 999, "path": ".github/workflows/" + path, "event": "pull_request", "head_sha": "c" * 40}
            self.status_data = {"queued": {"total_count": 1, "workflow_runs": [run]}}
            with self.subTest(path=path), patch.object(recovery, "github", side_effect=source):
                self.state = deepcopy(ORPHAN)
                self.calls = []
                self.assert_refused()
                # Without an active run of the changed workflow, recovery continues.
                self.status_data = {}
                self.state = deepcopy(ORPHAN)
                recovery.recover(self.ctx)
                self.assertEqual(len(self.breaks()), 1)

    def test_pagination_verifies_every_run_on_later_pages(self):
        runs = [
            {"id": number, "path": "dynamic/agents/copilot-pull-request-reviewer", "event": "dynamic"}
            for number in range(1000, 1101)
        ]
        original = self.github

        def pages(ctx, suffix):
            if "status=queued" in suffix:
                page = int(suffix.split("page=")[-1])
                return {"total_count": len(runs), "workflow_runs": runs[(page - 1) * 100 : page * 100]}
            return original(ctx, suffix)

        with patch.object(recovery, "github", side_effect=pages):
            recovery.recover(self.ctx)
            self.assertEqual(len(self.breaks()), 1)
            runs[-1] = {"id": 999}
            self.state = deepcopy(ORPHAN)
            self.calls = []
            self.assert_refused()

    def test_concurrency_api_validates_reusable_owner_job_and_attempt(self):
        self.members[0]["job_id"] = 10
        job = {
            "id": 10,
            "run_id": 123,
            "run_attempt": 1,
            "status": "in_progress",
            "name": "Deploy PR / Deploy Management",
        }
        original = self.github

        def api(ctx, suffix):
            return deepcopy(job) if suffix == "/actions/jobs/10" else original(ctx, suffix)

        with patch.object(recovery, "github", side_effect=api):
            recovery.verify_concurrency(self.ctx)
            for key, value in (("run_attempt", 2), ("run_id", 999), ("status", "completed"), ("name", "Other job")):
                before = job[key]
                job[key] = value
                with self.subTest(key=key), self.assertRaises(recovery.RecoveryError):
                    recovery.verify_concurrency(self.ctx)
                job[key] = before

    def test_concurrency_api_incomplete_queue_wrong_group_and_unknown_status_are_refused(self):
        good = {"group_name": "deploy-" + self.ctx["ref"], "total_count": 1, "group_members": deepcopy(self.members)}
        for data in (
            {},
            {**good, "group_name": None},
            {**good, "group_name": "deploy-other"},
            {**good, "total_count": 2},
            {**good, "total_count": True},
            {**good, "group_members": [{"run_id": 123, "status": "unknown"}]},
            {**good, "group_members": [{"run_id": "123", "status": "in_progress"}]},
        ):
            with (
                self.subTest(data=data),
                patch.object(recovery, "github", return_value=data),
                self.assertRaises(recovery.RecoveryError),
            ):
                recovery.verify_concurrency(self.ctx)

    def test_conditional_break_failure_is_not_retried(self):
        self.break_error = recovery.RecoveryError("ConditionNotMet")
        with self.assertRaisesRegex(recovery.RecoveryError, "ConditionNotMet"):
            recovery.recover(self.ctx)
        self.assertEqual(len(self.breaks()), 1)

    def test_failed_post_break_integrity_or_lease_check_stops_recovery(self):
        for update in (
            lambda value: value["properties"].update(etag='"changed"'),
            lambda value: value.update(metadata={"unexpected": "value"}),
            lambda value: value["properties"]["lease"].update(status="locked", state="leased"),
        ):
            self.calls = []
            self.state = deepcopy(ORPHAN)
            self.after_break = update
            with self.assertRaises(recovery.RecoveryError):
                recovery.recover(self.ctx)
            self.assertEqual(len(self.breaks()), 1)


class ExternalCommandTests(unittest.TestCase):
    def test_github_api_http_and_json_failures_are_closed(self):
        with patch.dict(os.environ, {"CI_RECOVERY_GITHUB_TOKEN": "test-token"}, clear=True):
            with patch.object(recovery.urllib.request, "urlopen", side_effect=urllib.error.URLError("unavailable")):
                with self.assertRaises(recovery.RecoveryError):
                    recovery.github({"repository": "microsoft/AzureTRE"}, "/actions/runs/123")
            with patch.object(recovery.urllib.request, "urlopen", return_value=io.StringIO("invalid")):
                with self.assertRaises(recovery.RecoveryError):
                    recovery.github({"repository": "microsoft/AzureTRE"}, "/actions/runs/123")

    def test_github_api_requires_and_sends_a_token(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(recovery.urllib.request, "urlopen") as urlopen:
            with self.assertRaisesRegex(recovery.RecoveryError, "actions: read"):
                recovery.github({"repository": "microsoft/AzureTRE"}, "/actions/runs/123")
            urlopen.assert_not_called()
        for env in ({"CI_RECOVERY_GITHUB_TOKEN": "recovery-token"}, {"GITHUB_TOKEN": "recovery-token"}):
            with (
                self.subTest(env=env),
                patch.dict(os.environ, env, clear=True),
                patch.object(recovery.urllib.request, "urlopen", return_value=io.StringIO("{}")) as urlopen,
            ):
                self.assertEqual(recovery.github({"repository": "microsoft/AzureTRE"}, "/actions/runs/123"), {})
                request = urlopen.call_args.args[0]
                self.assertEqual(request.get_header("Authorization"), "Bearer recovery-token")
                self.assertEqual(request.full_url, "https://api.github.com/repos/microsoft/AzureTRE/actions/runs/123")

    def test_azure_failures_and_invalid_json_are_closed(self):
        for result in (
            subprocess.CompletedProcess([], 1, "", "AuthorizationFailure"),
            subprocess.CompletedProcess([], 0, "invalid", ""),
        ):
            with patch.object(recovery.subprocess, "run", return_value=result):
                with self.assertRaises(recovery.RecoveryError):
                    recovery.azure({"subscription": "test-subscription"}, "storage", "blob", "show")


if __name__ == "__main__":
    unittest.main()

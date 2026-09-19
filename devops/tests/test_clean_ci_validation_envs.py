"""Exercise cleanup decisions with mocked Azure, GitHub, Git and date commands."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


CLEANUP_SCRIPT = Path(__file__).resolve().parents[1] / "scripts/clean_ci_validation_envs.sh"

MOCK_COMMAND = r'''
import json
import os
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlsplit

root = Path(os.environ["MOCK_ROOT"])
config = json.loads((root / "config.json").read_text())
command = Path(sys.argv[0]).name
args = sys.argv[1:]
with (root / "calls.jsonl").open("a") as log:
    log.write(json.dumps([command, *args]) + "\n")

if command == "gh":
    if args[0] == "api":
        endpoint = next(arg for arg in args if "actions/runs?" in arg)
        status = parse_qs(urlsplit(endpoint).query)["status"][0]
        if config.get("api_error") == status:
            sys.exit(1)
        if config.get("bad_response_status") == status:
            print(config["bad_response"])
            sys.exit(0)
        counts_file = root / "status_counts.json"
        counts = json.loads(counts_file.read_text()) if counts_file.exists() else {}
        counts[status] = counts.get(status, 0) + 1
        counts_file.write_text(json.dumps(counts))
        page_key = "later_pages" if counts[status] > 1 and "later_pages" in config else "pages"
        pages = config.get(page_key, {}).get(status, [{"workflow_runs": []}])
        for page in pages if "--paginate" in args else pages[:1]:
            print(json.dumps(page))
    elif args[:2] == ["pr", "list"]:
        print(json.dumps(config["open_prs"]))
    else:
        sys.exit("Unexpected gh command")
elif command == "az":
    if args[:2] == ["group", "list"]:
        query = args[args.index("--query") + 1]
        rows = config["groups"] if "ci_git_ref" in query else ["rg-main-ws-old"]
        for row in rows:
            print(row)
    elif args[:2] not in (["config", "set"], ["group", "delete"]):
        sys.exit("Unexpected az command")
elif command == "git":
    if args[0] == "for-each-ref":
        print("2026-09-18 00:00:00 +0000")
    elif args == ["show-ref"]:
        print("abc refs/remotes/origin/main")
    elif args[:2] == ["show-ref", "-q"]:
        sys.exit(1 if config.get("missing_branch") else 0)
    else:
        sys.exit("Unexpected git command")
elif command == "date":
    print(2000000000 - config["age_hours"] * 3600 if "-d" in args else 2000000000)
elif command not in ("control_tre.sh", "destroy_env_no_terraform.sh"):
    sys.exit("Unexpected command")
'''


class CleanupTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        for command in ("jq", "cut"):
            executable = shutil.which(command)
            if not executable:
                self.fail(f"Required command is missing: {command}")
            (bin_dir / command).symlink_to(executable)
        mock = self.root / "mock.py"
        mock.write_text(f"#!{sys.executable}\n" + MOCK_COMMAND)
        mock.chmod(0o755)
        for command in ("gh", "az", "git", "date"):
            (bin_dir / command).symlink_to(mock)
        scripts = self.root / "devops/scripts"
        scripts.mkdir(parents=True)
        for command in ("control_tre.sh", "destroy_env_no_terraform.sh"):
            (scripts / command).symlink_to(mock)
        self.config = {
            "age_hours": 6,
            "groups": ["rg-tretest\trefs/pull/5085/merge"],
            "open_prs": [{
                "number": 5085,
                "headRefName": "release/v0.29.1",
                "updatedAt": "2026-09-18T00:00:00Z",
            }],
        }
        # Only mocks and jq/cut are on PATH. No credentials reach the subprocess.
        self.env = {
            "PATH": str(bin_dir),
            "HOME": str(self.root),
            "MOCK_ROOT": str(self.root),
            "GITHUB_REPOSITORY": "example/tre",
            "GITHUB_RUN_ID": "123",
            "GITHUB_WORKFLOW": "Clean Validation Environments",
            "MAIN_TRE_ID": "main",
            "BRANCH_LAST_ACTIVITY_IN_HOURS_FOR_STOP": "4",
            "BRANCH_LAST_ACTIVITY_IN_HOURS_FOR_DESTROY": "48",
        }
        self.calls = []

    def run_cleanup(self):
        (self.root / "config.json").write_text(json.dumps(self.config))
        (self.root / "calls.jsonl").write_text("")
        (self.root / "status_counts.json").write_text("{}")
        result = subprocess.run(
            ["/bin/bash", str(CLEANUP_SCRIPT)], cwd=self.root, env=self.env,
            capture_output=True, text=True, timeout=30,
        )
        self.calls = [json.loads(line) for line in (self.root / "calls.jsonl").read_text().splitlines()]
        return result

    @staticmethod
    def workflow_run(run_id=456, branch="main"):
        return {
            "id": run_id,
            "name": "pr_comment_bot",
            "event": "issue_comment",
            "head_branch": branch,
            "pull_requests": [],
            "html_url": f"https://github.com/example/tre/actions/runs/{run_id}",
        }

    def assert_no_azure_calls(self):
        self.assertFalse(any(call[0] in (
            "az", "control_tre.sh", "destroy_env_no_terraform.sh",
        ) for call in self.calls), self.calls)

    def test_comment_triggered_pr_run_protects_stale_environment(self):
        for status in ("requested", "waiting", "pending", "queued", "in_progress"):
            with self.subTest(status=status):
                self.config["pages"] = {status: [{"workflow_runs": [self.workflow_run()]}]}
                result = self.run_cleanup()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assert_no_azure_calls()
                self.assertIn("Skipping environment cleanup", result.stdout)

    def test_active_run_on_another_branch_also_blocks_cleanup(self):
        self.config["pages"] = {"in_progress": [{"workflow_runs": [self.workflow_run(branch="feature/test")]}]}
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_no_azure_calls()

    def test_active_run_on_later_page_blocks_cleanup(self):
        self.config["pages"] = {"in_progress": [
            {"workflow_runs": [self.workflow_run(run_id=123)]},
            {"workflow_runs": [self.workflow_run()]},
        ]}
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("/runs/456", result.stdout)
        self.assert_no_azure_calls()

    def test_only_current_run_is_excluded(self):
        other_cleanup = self.workflow_run()
        other_cleanup["name"] = self.env["GITHUB_WORKFLOW"]
        self.config["pages"] = {"in_progress": [{"workflow_runs": [other_cleanup]}]}
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_no_azure_calls()

    def test_github_errors_prevent_all_cleanup(self):
        for status in ("requested", "waiting", "pending", "queued", "in_progress"):
            with self.subTest(status=status):
                self.config["api_error"] = status
                result = self.run_cleanup()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Could not check active workflow runs", result.stderr)
                self.assert_no_azure_calls()

    def test_invalid_or_empty_github_response_prevents_cleanup(self):
        for response in ("not json", "{}", ""):
            with self.subTest(response=response):
                self.config.update(bad_response_status="in_progress", bad_response=response)
                result = self.run_cleanup()
                self.assertNotEqual(result.returncode, 0)
                self.assert_no_azure_calls()

    def test_malformed_workflow_pages_prevent_cleanup(self):
        malformed_pages = (
            {"workflow_runs": {}},
            {"workflow_runs": {"unexpected": self.workflow_run(run_id=123)}},
            {"workflow_runs": None},
            {"workflow_runs": False},
            {"workflow_runs": ""},
            {"workflow_runs": 0},
            {}, [], None, True, 42, "invalid page",
        )
        for page in malformed_pages:
            for page_index in (0, 1):
                with self.subTest(page=page, page_index=page_index):
                    pages = [{"workflow_runs": []}] * page_index + [page]
                    self.config["pages"] = {"requested": pages}
                    result = self.run_cleanup()
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("Could not check active workflow runs", result.stderr)
                    self.assert_no_azure_calls()

    def test_valid_empty_workflow_pages_allow_cleanup(self):
        self.config["pages"] = {"requested": [
            {"workflow_runs": []},
            {"workflow_runs": []},
        ]}
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(["control_tre.sh", "stop"], self.calls)

    def test_malformed_recheck_prevents_main_workspace_cleanup(self):
        self.config["later_pages"] = {"requested": [{"workflow_runs": {}}]}
        result = self.run_cleanup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Could not check active workflow runs", result.stderr)
        self.assertIn(["control_tre.sh", "stop"], self.calls)
        self.assertFalse(any(call[:3] == ["az", "group", "delete"] for call in self.calls), self.calls)

    def test_missing_run_id_prevents_cleanup(self):
        del self.env["GITHUB_RUN_ID"]
        result = self.run_cleanup()
        self.assertNotEqual(result.returncode, 0)
        self.assert_no_azure_calls()

    def test_current_cleanup_run_allows_existing_stop_and_workspace_cleanup(self):
        self.config["pages"] = {"in_progress": [{"workflow_runs": [self.workflow_run(run_id=123)]}]}
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(["control_tre.sh", "stop"], self.calls)
        self.assertIn(["az", "group", "delete", "--yes", "--no-wait", "--name", "rg-main-ws-old"], self.calls)

    def test_new_run_blocks_main_workspace_cleanup(self):
        self.config["later_pages"] = {"in_progress": [{"workflow_runs": [self.workflow_run()]}]}
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(["control_tre.sh", "stop"], self.calls)
        self.assertFalse(any(call[:3] == ["az", "group", "delete"] for call in self.calls), self.calls)

    def test_idle_cleanup_still_destroys_expired_environments(self):
        self.config["age_hours"] = 49
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(["destroy_env_no_terraform.sh", "--core-tre-rg", "rg-tretest", "--no-wait"], self.calls)

    def test_idle_cleanup_still_destroys_closed_pr_environments(self):
        self.config["open_prs"] = []
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(["destroy_env_no_terraform.sh", "--core-tre-rg", "rg-tretest", "--no-wait"], self.calls)

    def test_idle_cleanup_still_destroys_removed_branch_environments(self):
        self.config.update(groups=["rg-tretest\trefs/heads/deleted"], missing_branch=True)
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(["destroy_env_no_terraform.sh", "--core-tre-rg", "rg-tretest", "--no-wait"], self.calls)


if __name__ == "__main__":
    unittest.main()

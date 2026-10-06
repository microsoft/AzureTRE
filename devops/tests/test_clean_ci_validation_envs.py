"""Exercise cleanup decisions and the real destroy helper with mocked services."""

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
import re
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
        if any("/pulls?" in arg for arg in args):
            if config.get("pr_api_error"):
                sys.exit(1)
            if "bad_pr_response" in config:
                print(config["bad_pr_response"])
                sys.exit(0)
            pages = config.get("pr_pages", [[{
                "number": pr["number"], "head": {"ref": pr["headRefName"]},
                "updated_at": pr["updatedAt"],
            } for pr in config["open_prs"]]])
            for page in pages if "--paginate" in args else pages[:1]:
                print(json.dumps(page))
            sys.exit(0)
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
        if "ci_git_ref" in query:
            if config.get("group_list_error"):
                sys.exit(1)
            if "bad_group_response" in config:
                print(config["bad_group_response"])
                sys.exit(0)
            print(json.dumps([{
                "name": row.split("\t")[0],
                "ci_git_ref": row.split("\t")[1] if "\t" in row else None,
            } for row in config["groups"]]))
        elif config.get("real_destroy") and query.endswith(".[name]"):
            if config.get("destroy_list_error"):
                sys.exit(1)
            prefix = re.search(r"starts_with\(name, '([^']+)'\)", query).group(1)
            for row in config.get("destroy_groups", config["groups"]):
                name = row.split("\t")[0]
                if name.startswith(prefix):
                    print(name)
        else:
            print("rg-main-ws-old")
    elif config.get("real_destroy") and args[:2] == ["group", "show"]:
        if config.get("group_show_error"):
            sys.exit(1)
        name = args[args.index("--name") + 1]
        sys.exit(0 if any(row.split("\t")[0] == name for row in config["groups"]) else 3)
    elif config.get("real_destroy") and args[:3] == ["group", "lock", "list"]:
        if config.get("core_lock_list_error"):
            sys.exit(1)
    elif config.get("real_destroy") and args[:2] in (["resource", "list"], ["acr", "list"], ["lock", "list"]):
        pass
    elif config.get("real_destroy") and args[:2] == ["keyvault", "list"]:
        if "--resource-group" in args:
            print(0)
    elif config.get("real_destroy") and (args[:2] == ["keyvault", "show"] or args[:4] == ["monitor", "log-analytics", "workspace", "show"]):
        sys.exit(3)
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

    def use_real_destroy_helper(self):
        self.config["real_destroy"] = True
        scripts = self.root / "devops/scripts"
        (scripts / "destroy_env_no_terraform.sh").unlink()
        for name in ("destroy_env_no_terraform.sh", "kv_add_network_exception.sh", "bash_trap_helper.sh"):
            shutil.copy2(CLEANUP_SCRIPT.parent / name, scripts / name)
        for command in ("bash", "dirname", "realpath", "sed", "sort", "tr", "xargs"):
            executable = shutil.which(command)
            if not executable:
                self.fail(f"Required command is missing: {command}")
            (self.root / "bin" / command).symlink_to(executable)

    def deleted_environment_groups(self):
        return [
            call[call.index("--resource-group") + 1] for call in self.calls
            if call[:3] == ["az", "group", "delete"] and "--resource-group" in call
        ]

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

    def environment_actions(self):
        return [call for call in self.calls if call[0] in ("control_tre.sh", "destroy_env_no_terraform.sh")]

    def test_management_only_closed_pr_uses_core_name_for_destroy(self):
        self.config.update(groups=["rg-tretest-mgmt\trefs/pull/5085/merge"], open_prs=[])
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.environment_actions(), [
            ["destroy_env_no_terraform.sh", "--core-tre-rg", "rg-tretest", "--no-wait"],
        ])

    def test_real_destroy_keeps_similarly_named_groups(self):
        self.use_real_destroy_helper()
        neighbours = ["rg-tretestother-mgmt", "rg-tretest-mgmt-copy", "rg-tretest-backup", "rg-tretest-wsother-abcd", "rg-tretest-svcother-abcd"]
        self.config.update(groups=["rg-tretest-mgmt\trefs/pull/5085/merge", *neighbours], open_prs=[])
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.deleted_environment_groups(), ["rg-tretest-mgmt"])
        for call in self.calls:
            if call[:3] in (["az", "acr", "list"], ["az", "lock", "list"]):
                self.assertNotIn(call[call.index("--resource-group") + 1], neighbours)

    def test_real_destroy_deletes_only_the_environment_groups_once(self):
        self.use_real_destroy_helper()
        groups = ["rg-tretest\trefs/pull/5085/merge", "rg-tretest-mgmt\trefs/pull/5085/merge",
                  "rg-tretest-ws-abcd", "rg-tretest-svc-abcd", "rg-tretestother", "rg-tretestother-ws-abcd", "rg-tretestother-svc-abcd"]
        for rows in (groups, list(reversed(groups))):
            with self.subTest(rows=rows):
                self.config.update(groups=rows, open_prs=[])
                result = self.run_cleanup()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.deleted_environment_groups(), ["rg-tretest-ws-abcd", "rg-tretest-svc-abcd", "rg-tretest-mgmt", "rg-tretest"])

    def test_real_destroy_skips_when_only_neighbour_remains(self):
        self.use_real_destroy_helper()
        self.config.update(groups=["rg-tretest-mgmt\trefs/pull/5085/merge"],
                           destroy_groups=["rg-tretestother-mgmt"], open_prs=[])
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.deleted_environment_groups(), [])
        self.assertIn("No resource groups found for environment", result.stdout)

    def test_real_destroy_inventory_failure_prevents_deletion(self):
        self.use_real_destroy_helper()
        self.config.update(groups=["rg-tretest-mgmt\trefs/pull/5085/merge"], destroy_list_error=True, open_prs=[])
        result = self.run_cleanup()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(call[:3] == ["az", "group", "delete"] for call in self.calls))

    def test_real_destroy_inventory_requires_core_preparation_despite_lookup_error(self):
        self.use_real_destroy_helper()
        self.config.update(groups=["rg-tretest\trefs/pull/5085/merge", "rg-tretest-mgmt"],
                           group_show_error=True, open_prs=[])
        core_inspection = ["az", "group", "lock", "list", "-g", "rg-tretest", "--query", "[].id", "-o", "tsv"]
        for inspection_error in (False, True):
            with self.subTest(inspection_error=inspection_error):
                self.config["core_lock_list_error"] = inspection_error
                result = self.run_cleanup()
                self.assertIn(core_inspection, self.calls)
                if inspection_error:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(any(call[:3] == ["az", "group", "delete"] for call in self.calls))
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(self.deleted_environment_groups(), ["rg-tretest-mgmt", "rg-tretest"])
                    first_delete = next(index for index, call in enumerate(self.calls) if call[:3] == ["az", "group", "delete"])
                    self.assertLess(self.calls.index(core_inspection), first_delete)

    def test_real_destroy_uses_latest_inventory_when_core_disappears(self):
        self.use_real_destroy_helper()
        self.config.update(groups=["rg-tretest\trefs/pull/5085/merge", "rg-tretest-mgmt"],
                           destroy_groups=["rg-tretest-mgmt"], core_lock_list_error=True, open_prs=[])
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.deleted_environment_groups(), ["rg-tretest-mgmt"])
        self.assertFalse(any(call[:4] == ["az", "group", "lock", "list"] for call in self.calls))

    def test_management_only_expired_pr_is_destroyed(self):
        self.config.update(groups=["rg-tretest-mgmt\trefs/pull/5085/merge"], age_hours=49)
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.environment_actions(), [
            ["destroy_env_no_terraform.sh", "--core-tre-rg", "rg-tretest", "--no-wait"],
        ])

    def test_management_only_missing_branch_is_destroyed(self):
        self.config.update(groups=["rg-tretest-mgmt\trefs/heads/deleted"], missing_branch=True)
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.environment_actions(), [
            ["destroy_env_no_terraform.sh", "--core-tre-rg", "rg-tretest", "--no-wait"],
        ])

    def test_management_only_branch_obeys_destroy_threshold(self):
        self.config["groups"] = ["rg-tretest-mgmt\trefs/heads/feature/test"]
        for age in (1, 6, 48, 49):
            with self.subTest(age=age):
                self.config["age_hours"] = age
                result = self.run_cleanup()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(len(self.environment_actions()), 1 if age > 48 else 0)
                self.assertNotIn(["control_tre.sh", "stop"], self.calls)

    def test_management_only_pr_is_not_stopped_or_destroyed_early(self):
        self.config["groups"] = ["rg-tretest-mgmt\trefs/pull/5085/merge"]
        for age in (1, 6, 48):
            with self.subTest(age=age):
                self.config["age_hours"] = age
                result = self.run_cleanup()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.environment_actions(), [])

    def test_paired_core_and_management_are_destroyed_once_in_either_order(self):
        groups = ["rg-tretest\trefs/pull/5085/merge", "rg-tretest-mgmt\trefs/pull/5085/merge"]
        self.config["open_prs"] = []
        for rows in (groups, list(reversed(groups))):
            with self.subTest(rows=rows):
                self.config["groups"] = rows
                result = self.run_cleanup()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.environment_actions(), [
                    ["destroy_env_no_terraform.sh", "--core-tre-rg", "rg-tretest", "--no-wait"],
                ])

    def test_paired_environment_only_stops_core(self):
        self.config["groups"] = ["rg-tretest-mgmt\trefs/pull/5085/merge", "rg-tretest\trefs/pull/5085/merge"]
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.environment_actions(), [["control_tre.sh", "stop"]])

    def test_management_with_untagged_core_is_not_an_orphan(self):
        self.config.update(groups=["rg-tretest-mgmt\trefs/pull/5085/merge", "rg-tretest"], open_prs=[])
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.environment_actions(), [])

    def test_untagged_legacy_management_orphan_is_untouched(self):
        self.config.update(groups=["rg-tretest-mgmt"], open_prs=[])
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.environment_actions(), [])

    def test_non_ci_management_group_is_untouched(self):
        self.config.update(groups=["rg-tretest-mgmt\tmanual", "rg-treother-mgmt\trefs/not-a-ci-ref"], open_prs=[])
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.environment_actions(), [])

    def test_active_run_protects_management_only_environment(self):
        self.config.update(groups=["rg-tretest-mgmt\trefs/pull/5085/merge"], open_prs=[])
        self.config["pages"] = {"in_progress": [{"workflow_runs": [self.workflow_run()]}]}
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_no_azure_calls()

    def test_open_pr_on_later_page_is_not_mistaken_for_closed(self):
        self.config.update(groups=["rg-tretest-mgmt\trefs/pull/5085/merge"], age_hours=1, open_prs=[])
        first_page = [{
            "number": number, "head": {"ref": "feature/other"}, "updated_at": "2026-09-18T00:00:00Z",
        } for number in range(1, 101)]
        self.config["pr_pages"] = [first_page, [{
            "number": 5085, "head": {"ref": "feature/test"}, "updated_at": "2026-09-18T00:00:00Z",
        }]]
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.environment_actions(), [])

    def test_pr_api_error_prevents_deletion(self):
        self.config["pr_api_error"] = True
        result = self.run_cleanup()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.environment_actions(), [])
        self.assertFalse(any(call[:3] == ["az", "group", "delete"] for call in self.calls))

    def test_invalid_pr_response_prevents_deletion(self):
        for response in ("", "{}", "not json", '[{"number": 5085}]'):
            with self.subTest(response=response):
                self.config["bad_pr_response"] = response
                result = self.run_cleanup()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.environment_actions(), [])
                self.assertFalse(any(call[:3] == ["az", "group", "delete"] for call in self.calls))

    def test_resource_group_query_error_prevents_deletion(self):
        self.config["group_list_error"] = True
        result = self.run_cleanup()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.environment_actions(), [])
        self.assertFalse(any(call[:3] == ["az", "group", "delete"] for call in self.calls))

    def test_invalid_group_response_prevents_deletion(self):
        for response in ("", " ", "[] []", "null", "{}", '[{}]', '[{"name": "rg-tretest-mgmt", "ci_git_ref": 42}]'):
            with self.subTest(response=response):
                self.config["bad_group_response"] = response
                result = self.run_cleanup()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.environment_actions(), [])
                self.assertFalse(any(call[:3] == ["az", "group", "delete"] for call in self.calls))

    def test_no_tagged_groups_preserves_main_workspace_cleanup(self):
        self.config["groups"] = []
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.environment_actions(), [])
        self.assertIn(["az", "group", "delete", "--yes", "--no-wait", "--name", "rg-main-ws-old"], self.calls)


if __name__ == "__main__":
    unittest.main()

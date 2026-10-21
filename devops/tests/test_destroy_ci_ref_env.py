"""Verify cleanup ownership across legacy and regional CI namespaces."""

from copy import deepcopy
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import destroy_ci_ref_env as cleanup  # noqa: E402

REF = "refs/pull/5092/merge"
SUBSCRIPTION = "test-subscription"


def group(name, ref=REF, subscription=SUBSCRIPTION):
    return {"name": name, "id": f"/subscriptions/{subscription}/resourceGroups/{name}", "tags": {"ci_git_ref": ref}}


class CleanupTests(unittest.TestCase):
    def setUp(self):
        names = (
            "rg-trea66984da",
            "rg-trea66984da-mgmt",
            "rg-tree06583c4",
            "rg-tree06583c4-mgmt",
            "rg-tre637595c5-mgmt",
        )
        self.groups = [group(name) for name in names]
        self.groups += [
            group("rg-tre12345678", "refs/pull/1/merge"),
            group("rg-treproduction"),
            group("rg-trea66984da-ws-workspace"),
            {"name": "rg-unowned", "tags": None},
        ]
        # Keep the upstream defaults when a fork's CI runs these tests with its own values.
        env = patch.dict(os.environ, {"GITHUB_REPOSITORY": "microsoft/AzureTRE", "CI_ENV_PREFIX": ""})
        env.start()
        self.addCleanup(env.stop)
        self.reads = 0
        self.account = SUBSCRIPTION
        self.change = None
        self.change_account = False
        self.azure_patch = patch.object(cleanup, "azure", side_effect=self.azure)
        self.azure_patch.start()
        self.addCleanup(self.azure_patch.stop)
        self.run_patch = patch.object(cleanup.subprocess, "run")
        self.run = self.run_patch.start()
        self.addCleanup(self.run_patch.stop)

    def azure(self, subscription, *args):
        self.assertEqual(subscription, SUBSCRIPTION)
        if args == ("account", "show"):
            account = self.account
            if self.change_account:
                self.account = "other-subscription"
            return {"id": account}
        if args == ("group", "list"):
            self.reads += 1
            if self.reads == 2 and self.change:
                self.change(self.groups)
            return deepcopy(self.groups)
        self.assertEqual(args[:3], ("group", "show", "--name"))
        return deepcopy(next(row for row in self.groups if row["name"] == args[3]))

    def test_destroy_all_owned_generations_using_existing_helper(self):
        cleanup.destroy(REF, SUBSCRIPTION)
        calls = [call.args[0] for call in self.run.call_args_list]
        self.assertEqual([call[-1] for call in calls], ["rg-tre637595c5", "rg-trea66984da", "rg-tree06583c4"])
        for call in calls:
            self.assertEqual(call[0], "bash")
            self.assertTrue(call[1].endswith("destroy_env_no_terraform.sh"))
            self.assertEqual(call[2], "--core-tre-rg")

    def test_unknown_ref_has_no_mutations(self):
        cleanup.destroy("refs/pull/99/merge", SUBSCRIPTION)
        self.run.assert_not_called()

    def test_branch_cleanup_only_selects_its_own_reference(self):
        self.groups.append(group("rg-treabcdef12", "refs/heads/fix/keyvault"))
        cleanup.destroy("refs/heads/fix/keyvault", SUBSCRIPTION)
        self.assertEqual(self.run.call_args.args[0][-1], "rg-treabcdef12")

    def test_other_prefix_groups_are_outside_the_fork_namespace(self):
        self.groups.append(group("rg-frka66984da"))
        with patch.dict(os.environ, {"CI_ENV_PREFIX": "frk"}):
            cleanup.destroy(REF, SUBSCRIPTION)
        self.assertEqual([call.args[0][-1] for call in self.run.call_args_list], ["rg-frka66984da"])

    def test_fork_without_a_prefix_is_refused(self):
        self.groups.append(group("rg-trea66984da-ws-extra"))
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "contoso/AzureTRE"}), self.assertRaises(ValueError):
            cleanup.destroy(REF, SUBSCRIPTION)
        self.run.assert_not_called()

    def test_fork_with_the_default_prefix_refuses_untagged_groups(self):
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "contoso/AzureTRE", "CI_ENV_PREFIX": "tre"}):
            with self.assertRaises(ValueError):
                cleanup.destroy(REF, SUBSCRIPTION)
        self.run.assert_not_called()

    def test_missing_repository_is_refused(self):
        # With another prefix the ownership rule accepts untagged groups, so only the guard can refuse.
        self.groups.extend([group("rg-frka66984da"), group("rg-frka66984da-mgmt")])
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "", "CI_ENV_PREFIX": "frk"}):
            with patch.object(cleanup, "verify_account") as verify, self.assertRaises(ValueError):
                cleanup.destroy(REF, SUBSCRIPTION)
        verify.assert_not_called()
        self.run.assert_not_called()

    def test_default_prefix_ignores_fork_groups(self):
        self.groups.append(group("rg-frka66984da"))
        with patch.dict(os.environ, {"CI_ENV_PREFIX": ""}):
            cleanup.destroy(REF, SUBSCRIPTION)
        self.assertNotIn("rg-frka66984da", [call.args[0][-1] for call in self.run.call_args_list])

    def test_group_tagged_by_another_repository_stops_cleanup(self):
        for row in self.groups:
            if (row.get("tags") or {}).get("ci_git_ref") == REF:
                row["tags"]["ci_repository"] = "contoso/AzureTRE"
        for repository, refused in (("contoso/AzureTRE", False), ("microsoft/AzureTRE", True), ("", True)):
            self.run.reset_mock()
            env = {"GITHUB_REPOSITORY": repository, "CI_ENV_PREFIX": "tre"}
            with self.subTest(repository=repository), patch.dict(os.environ, env):
                if refused:
                    with self.assertRaises(ValueError):
                        cleanup.destroy(REF, SUBSCRIPTION)
                    self.run.assert_not_called()
                else:
                    cleanup.destroy(REF, SUBSCRIPTION)
                    self.assertEqual(self.run.call_count, 3)

    def test_tag_names_in_another_case_keep_their_owner(self):
        for row in self.groups:
            tags = row.get("tags") or {}
            if tags.get("ci_git_ref") == REF:
                row["tags"] = {"CI_Git_Ref": tags["ci_git_ref"], "CI_Repository": "contoso/AzureTRE"}
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "microsoft/AzureTRE", "CI_ENV_PREFIX": "tre"}):
            with self.assertRaisesRegex(ValueError, "Another repository owns"):
                cleanup.destroy(REF, SUBSCRIPTION)
        self.run.assert_not_called()

    def test_main_or_invalid_ref_has_no_mutations(self):
        for ref in ("refs/heads/main", "refs/pull/5092/head", "refs/heads/x\ny"):
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                cleanup.destroy(ref, SUBSCRIPTION)
        self.run.assert_not_called()

    def test_core_and_management_ownership_must_match(self):
        for tags in ({"ci_git_ref": "refs/pull/99/merge"}, {}, None):
            self.groups[1]["tags"] = tags
            with self.subTest(tags=tags), self.assertRaises(ValueError):
                cleanup.destroy(REF, SUBSCRIPTION)
        self.run.assert_not_called()

    def test_foreign_resource_id_has_no_mutations(self):
        self.groups[0]["id"] = group("rg-trea66984da", subscription="other-subscription")["id"]
        with self.assertRaises(ValueError):
            cleanup.destroy(REF, SUBSCRIPTION)
        self.run.assert_not_called()

    def test_invalid_inventory_has_no_mutations(self):
        cases = [
            None,
            {},
            [None],
            [{"name": 3}],
            [group("rg-tre12345678"), group("rg-tre12345678")],
            [{"name": "rg-trea66984da", "tags": "invalid"}],
        ]
        for groups in cases:
            with self.subTest(groups=groups), self.assertRaises(ValueError):
                cleanup.targets(groups, REF, SUBSCRIPTION, "")
        self.run.assert_not_called()

    def test_inventory_permissions_error_has_no_mutations(self):
        with patch.object(cleanup, "azure", side_effect=subprocess.CalledProcessError(1, "az")):
            with self.assertRaises(subprocess.CalledProcessError):
                cleanup.destroy(REF, SUBSCRIPTION)
        self.run.assert_not_called()

    def test_invalid_account_has_no_mutations(self):
        for account in (None, [], {}, {"id": None}, {"id": 3}):
            with (
                self.subTest(account=account),
                patch.object(cleanup, "azure", return_value=account),
                self.assertRaises(ValueError),
            ):
                cleanup.destroy(REF, SUBSCRIPTION)
        self.run.assert_not_called()

    def test_changed_ownership_stops_before_destroy(self):
        self.change = lambda groups: groups[4]["tags"].update(ci_git_ref="refs/pull/99/merge")
        with self.assertRaises(ValueError):
            cleanup.destroy(REF, SUBSCRIPTION)
        self.run.assert_not_called()

    def test_default_subscription_must_match_and_remain_unchanged(self):
        for changed in (False, True):
            self.account = SUBSCRIPTION if changed else "other-subscription"
            self.change_account = changed
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                cleanup.destroy(REF, SUBSCRIPTION)
        self.run.assert_not_called()

    def test_child_failure_stops_remaining_cleanup(self):
        self.run.side_effect = subprocess.CalledProcessError(1, "bash")
        with self.assertRaises(subprocess.CalledProcessError):
            cleanup.destroy(REF, SUBSCRIPTION)
        self.assertEqual(self.run.call_count, 1)


class AzureCommandTests(unittest.TestCase):
    def test_default_account_is_checked_and_inventory_is_subscription_scoped(self):
        with patch.object(cleanup.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "{}")) as run:
            cleanup.azure(SUBSCRIPTION, "account", "show")
            self.assertNotIn("--subscription", run.call_args.args[0])
            cleanup.azure(SUBSCRIPTION, "group", "list")
            self.assertIn("--subscription", run.call_args.args[0])
            self.assertIn(SUBSCRIPTION, run.call_args.args[0])


if __name__ == "__main__":
    unittest.main()

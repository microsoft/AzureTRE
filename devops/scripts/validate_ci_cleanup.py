"""Validate bootstrap and cleanup using owned, empty Azure resource groups."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid


SOURCE = Path(__file__).resolve().parents[2]
OWNER_TAG = "cleanup_validation_run"
DISCOVERY = "[?starts_with(name, 'rg-tre')].{name:name, ci_git_ref:tags.ci_git_ref}"
STORAGE_NAME = "validationnevercreated"


class ValidationError(Exception):
    """A validation assertion or scope check failed."""


class Incomplete(ValidationError):
    """Another workflow prevented the cleanup test from running."""


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def inventory_digest(rows, fixtures):
    remaining = [{"name": row["name"], "tags": row.get("tags") or {}}
                 for row in rows if row["name"] not in fixtures]
    return hashlib.sha256(json.dumps(sorted(remaining, key=lambda row: row["name"]), sort_keys=True).encode()).hexdigest()


class Validation:
    def __init__(self, directory):
        self.root = Path(directory).resolve()
        self.path = self.root / "state.json"
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {}

    def save(self):
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.state, indent=2) + "\n")
        temporary.replace(self.path)

    def audit(self, operation):
        with (self.root / "audit.jsonl").open("a") as stream:
            stream.write(json.dumps({"phase": os.environ.get("CLEANUP_VALIDATION_PHASE"), "operation": operation}) + "\n")

    def azure(self, args, check=True):
        result = subprocess.run([self.state["az"], *args, "--subscription", self.state["subscription"], "--only-show-errors"],
                                capture_output=True, text=True, timeout=150)
        if check:
            require(result.returncode == 0, f"Azure CLI {' '.join(args[:2])} failed (exit {result.returncode}). Raw Azure output is withheld.")
        return result

    def azure_json(self, args):
        return json.loads(self.azure([*args, "--output", "json"]).stdout)

    def identity(self):
        account = self.azure_json(["account", "show"])
        actual = [account["id"], account["tenantId"], account["user"]["name"], account["user"]["type"]]
        require(actual == self.state["identity"], "The Azure identity changed during validation.")

    def check(self, name, condition):
        self.state.setdefault("checks", []).append({"name": name, "passed": bool(condition)})
        self.save()
        require(condition, name + " failed.")
        print("PASS: " + name, flush=True)

    def owned_group(self, group):
        require(group in self.state["groups"], "The resource group is outside this validation run.")
        self.identity()
        metadata = self.azure_json(["group", "show", "--name", group])
        expected_id = f'/subscriptions/{self.state["subscription"]}/resourceGroups/{group}'
        require(metadata["id"].lower() == expected_id.lower(), "The resource group identity does not match.")
        require((metadata.get("tags") or {}).get(OWNER_TAG) == self.state["owner"], "The validation ownership tag does not match.")
        return metadata

    def owned_empty(self, group):
        metadata = self.owned_group(group)
        require(metadata["properties"]["provisioningState"] == "Succeeded", "The validation group is not ready.")
        require(self.azure_json(["resource", "list", "--resource-group", group]) == [], "The validation group contains resources.")
        require(self.azure_json(["lock", "list", "--resource-group", group]) == [], "The validation group has locks.")
        return metadata

    def initialise(self, location):
        require(not self.state, "Use a fresh state directory for each validation run.")
        require(os.environ.get("GITHUB_ACTIONS") == "true", "Run live validation from GitHub Actions.")
        run_id, attempt = os.environ["GITHUB_RUN_ID"], os.environ["GITHUB_RUN_ATTEMPT"]
        require(re.fullmatch(r"[0-9]{1,20}", run_id) and re.fullmatch(r"[0-9]{1,6}", attempt), "Invalid workflow run identifier.")
        require(re.fullmatch(r"[a-z0-9]+", location), "Use an Azure location name, such as westeurope.")
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=SOURCE, text=True).strip()
        require(commit == os.environ["GITHUB_SHA"], "The checkout does not match the workflow commit.")
        require(subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "devops/scripts", "devops/terraform/bootstrap.sh"],
                               cwd=SOURCE).returncode == 0, "Validation requires an unchanged checkout.")
        token = f"{run_id}-{attempt}-{uuid.uuid4().hex[:8]}"
        core = "rg-trevalidate-" + token
        branch = "ci-cleanup-validation/" + token
        require(subprocess.run(["git", "show-ref", "--verify", "--quiet", "refs/remotes/origin/" + branch],
                               cwd=SOURCE).returncode == 1, "The synthetic cleanup branch already exists.")
        self.state = {"az": shutil.which("az"), "subscription": os.environ["AZURE_SUBSCRIPTION_ID"],
                      "tenant": os.environ["AZURE_TENANT_ID"], "commit": commit, "run_id": run_id, "attempt": attempt,
                      "location": location, "owner": token, "core": core, "groups": [core + "-mgmt", core + "other-mgmt"],
                      "ref": "refs/heads/" + branch, "main_id": "validation-disabled-" + token, "checks": [], "status": "running"}
        require(self.state["az"] and self.state["subscription"] and self.state["tenant"], "Azure configuration is missing.")
        account = self.azure_json(["account", "show"])
        require(account["id"] == self.state["subscription"] and account["tenantId"] == self.state["tenant"], "Unexpected Azure account.")
        self.state["identity"] = [account["id"], account["tenantId"], account["user"]["name"], account["user"]["type"]]
        groups = self.azure_json(["group", "list"])
        require(not any(row["name"].lower().startswith(core.lower()) for row in groups), "A generated fixture name already exists.")
        self.state["inventory"] = inventory_digest(groups, [])
        self.save()
        self.check("Workflow commit and Azure identity verified", True)

    def wrapper_environment(self, phase):
        bindir = self.root / "bin"
        bindir.mkdir(exist_ok=True)
        wrapper = bindir / "az"
        wrapper.write_text(f"#!{sys.executable}\nimport sys\nsys.path.insert(0, {str(Path(__file__).parent)!r})\n"
                           "from validate_ci_cleanup import guard_main\nsys.exit(guard_main())\n")
        wrapper.chmod(0o755)
        env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ["PATH"],
                   CLEANUP_VALIDATION_STATE=str(self.root), CLEANUP_VALIDATION_PHASE=phase)
        for name in ("TRE_ID", "PRIVATE_AGENT_SUBNET_ID", "PYTHONPATH", "PYTHONOPTIMIZE"):
            env.pop(name, None)
        return env

    def script(self, name, env):
        result = subprocess.run(["/bin/bash", str(SOURCE / name)], cwd=SOURCE, env=env, capture_output=True, text=True, timeout=240)
        # Source scripts can print subscription data. Keep raw output out of artifacts and the job log.
        return result

    def bootstrap(self, name, group, ref, expected):
        env = self.wrapper_environment("bootstrap")
        env.update(TF_VAR_mgmt_resource_group_name=group, TF_VAR_mgmt_storage_account_name=STORAGE_NAME,
                   LOCATION=self.state["location"], TF_VAR_enable_cmk_encryption="false")
        env.pop("TF_VAR_ci_git_ref", None)
        if ref is not None:
            env["TF_VAR_ci_git_ref"] = ref
        result = self.script("devops/terraform/bootstrap.sh", env)
        require(result.returncode == 39, "Bootstrap did not stop at the injected storage failure.")
        metadata = self.owned_empty(group)
        self.check(name, metadata["tags"] == {OWNER_TAG: self.state["owner"], **expected})

    def set_tags(self, group, tags):
        self.owned_empty(group)
        self.azure(["group", "update", "--name", group, "--set", *[f"tags.{key}={value}" for key, value in tags.items()]])

    def scenarios(self):
        target, neighbour = self.state["groups"]
        ref = self.state["ref"]
        self.bootstrap("New CI group tagged before storage failure", target, ref, {"ci_git_ref": ref})
        self.set_tags(target, {"validation_keep": "preserved"})
        self.bootstrap("CI rerun preserves unrelated tags", target, ref + "/rerun", {"ci_git_ref": ref + "/rerun", "validation_keep": "preserved"})
        self.bootstrap("New non-CI group has no CI ownership tag", neighbour, None, {})
        self.bootstrap("Existing group receives a CI ownership tag", neighbour, ref, {"ci_git_ref": ref})
        self.set_tags(neighbour, {"validation_keep": "preserved"})
        expected = {"ci_git_ref": ref, "validation_keep": "preserved"}
        self.bootstrap("Empty CI reference preserves tags", neighbour, "", expected)
        self.bootstrap("Unset CI reference preserves tags", neighbour, None, expected)
        self.bootstrap("CI reference can be restored", target, ref, expected)
        self.bootstrap("Repeated CI bootstrap preserves tags", target, ref, expected)
        tags = dict(self.owned_empty(neighbour)["tags"])
        del tags["ci_git_ref"]
        # az group update supports replacing tags, but rejects --remove.
        self.azure(["group", "update", "--name", neighbour, "--tags", *[f"{key}={value}" for key, value in tags.items()]])
        self.check("Neighbour CI reference removed without changing other tags", self.owned_empty(neighbour)["tags"] == tags)
        self.state["neighbour_tags"] = tags
        self.save()

    def cleanup_script(self, preview):
        phase = "preview" if preview else "apply"
        env = self.wrapper_environment(phase)
        env.update(MAIN_TRE_ID=self.state["main_id"], BRANCH_LAST_ACTIVITY_IN_HOURS_FOR_STOP="4",
                   BRANCH_LAST_ACTIVITY_IN_HOURS_FOR_DESTROY="48")
        result = self.script("devops/scripts/clean_ci_validation_envs.sh", env)
        audit = self.root / "audit.jsonl"
        events = [json.loads(line) for line in audit.read_text().splitlines()] if audit.exists() else []
        events = [item["operation"] for item in events if item["phase"] == phase]
        require("refused" not in events, "The cleanup script attempted an operation outside the fixture scope.")
        if result.returncode == 0 and "Skipping environment cleanup while other workflow runs are " in result.stdout:
            raise Incomplete("Another workflow is active. Fixtures will be removed; run validation again when the repository is idle.")
        require(result.returncode == 0, "The cleanup script failed.")
        operation = "preview_delete" if preview else "delete"
        self.check("Cleanup " + phase + " selected exactly one target", events.count(operation) == 1)
        target, neighbour = self.state["groups"]
        if preview:
            self.owned_empty(target)
        else:
            self.wait_deleted(target)
        self.check("Neighbour preserved after " + phase, self.owned_empty(neighbour)["tags"] == self.state["neighbour_tags"])

    def wait_deleted(self, group):
        self.azure(["group", "wait", "--name", group, "--deleted", "--interval", "5", "--timeout", "120"])
        require(self.azure_json(["group", "exists", "--name", group]) is False, "A disposable group still exists.")

    def cleanup_fixtures(self):
        if not self.state:
            return
        failures = []
        for group in self.state["groups"]:
            try:
                if self.azure_json(["group", "exists", "--name", group]):
                    metadata = self.owned_group(group)
                    if metadata["properties"]["provisioningState"] != "Deleting":
                        self.owned_empty(group)
                        self.azure(["group", "delete", "--name", group, "--yes", "--no-wait"])
                    self.wait_deleted(group)
            except (ValidationError, KeyError, ValueError, OSError, subprocess.SubprocessError):
                failures.append(group)
        self.state["fixtures_deleted"] = not failures
        self.state["inventory_unchanged"] = inventory_digest(self.azure_json(["group", "list"]), self.state["groups"]) == self.state["inventory"]
        self.save()
        require(not failures, "Fixture cleanup failed. Inspect the run's ownership tag before manual recovery.")
        require(self.state["inventory_unchanged"], "The non-fixture resource-group inventory changed during validation.")
        print("All fixtures are absent. Non-fixture group names and tags are unchanged.", flush=True)

    def guard(self, args):
        phase = os.environ["CLEANUP_VALIDATION_PHASE"]
        target, neighbour = self.state["groups"]
        if phase == "bootstrap":
            group, ref = os.environ["TF_VAR_mgmt_resource_group_name"], os.environ.get("TF_VAR_ci_git_ref", "")
            require(group in self.state["groups"], "Bootstrap targeted a group outside the fixtures.")
            create = ["group", "create", "--resource-group", group, "--location", self.state["location"],
                      *(["--tags", "ci_git_ref=" + ref] if ref else []), "-o", "table"]
            if args == ["group", "exists", "--name", group, "--output", "json"]:
                return self.forward(args)
            if args == create:
                self.identity()
                if self.azure_json(["group", "exists", "--name", group]):
                    self.owned_empty(group)
                # Add the fixture marker atomically, including when bootstrap is non-CI.
                args = [*args[:-2], *([] if ref else ["--tags"]), f"{OWNER_TAG}={self.state['owner']}", *args[-2:]]
                return self.forward(args)
            if args == ["group", "update", "--name", group, "--set", "tags.ci_git_ref=" + ref, "-o", "table"]:
                self.owned_empty(group)
                return self.forward(args)
            if args == ["storage", "account", "show", "--resource-group", group, "--name", STORAGE_NAME, "--query", "name", "-o", "none"]:
                return 3
            if args == ["storage", "account", "create", "--resource-group", group, "--name", STORAGE_NAME,
                        "--location", self.state["location"], "--allow-blob-public-access", "false", "--min-tls-version", "TLS1_2",
                        "--kind", "StorageV2", "--sku", "Standard_LRS", "-o", "table", "--encryption-key-type-for-queue", "Service",
                        "--encryption-key-type-for-table", "Service", "--require-infrastructure-encryption", "true"]:
                self.audit("storage_creation_blocked")
                return 39
        elif phase in ("preview", "apply"):
            core = self.state["core"]
            if args == ["config", "set", "extension.use_dynamic_install=yes_without_prompt"]:
                return 0
            if args == ["group", "list", "--query", f"[?starts_with(name, 'rg-{self.state['main_id']}-ws-')].name", "-o", "tsv"]:
                self.audit("main_workspace_sweep_excluded")
                return 0
            if args == ["group", "list", "--query", DISCOVERY, "-o", "json"]:
                rows = json.loads(self.azure(args).stdout)
                print(json.dumps([row for row in rows if row["name"] in self.state["groups"]]))
                return 0
            if args == ["group", "list", "--query", f"[?starts_with(name, '{core}')].[name]", "-o", "tsv"]:
                names = self.azure(args).stdout.split()
                require(set(names) == set(self.state["groups"]), "Unexpected groups share the disposable prefix.")
                # Return both fixtures so the real helper must exclude the neighbour.
                print("\n".join(names))
                return 0
            if args == ["keyvault", "list", "--query", f"[?name=='kv-{core.removeprefix('rg-')}'].id", "--output", "tsv"]:
                require(not self.azure(args).stdout.strip(), "An unexpected core Key Vault exists.")
                return 0
            if args in (["acr", "list", "--resource-group", target, "--query", "[].name", "--output", "tsv"],
                        ["lock", "list", "--resource-group", target, "--query", "[].id", "-o", "tsv"]):
                require(not self.azure(args).stdout.strip(), "The disposable group contains a registry or a lock.")
                return 0
            if args == ["group", "delete", "--resource-group", target, "--yes", "--no-wait"]:
                metadata = self.owned_empty(target)
                require(metadata["tags"].get("ci_git_ref") == self.state["ref"], "The cleanup ownership reference changed.")
                if phase == "preview":
                    self.audit("preview_delete")
                    return 0
                result = self.forward(args)
                self.audit("delete")
                return result
        raise ValidationError("An Azure command is outside the validation allow-list.")

    def forward(self, args, check=True):
        result = self.azure(args, check=check)
        sys.stdout.write(result.stdout)
        # The caller captures raw output. It is never uploaded as evidence.
        sys.stderr.write(result.stderr)
        return result.returncode

    def summary(self):
        complete = self.state.get("status") == "passed" and self.state.get("fixtures_deleted") and self.state.get("inventory_unchanged")
        status = "passed" if complete else self.state.get("status", "not_run")
        if status in ("passed", "running"):
            status = "incomplete"
        report = {"status": status, "commit": self.state.get("commit", os.environ.get("GITHUB_SHA", "")),
                  "checks": self.state.get("checks", []), "fixture_owner": self.state.get("owner", ""),
                  "fixtures_deleted": self.state.get("fixtures_deleted", False),
                  "non_fixture_inventory_unchanged": self.state.get("inventory_unchanged", False)}
        if complete:
            report["status"] = "passed"
        evidence = self.root / "evidence"
        evidence.mkdir(parents=True, exist_ok=True)
        (evidence / "results.json").write_text(json.dumps(report, indent=2) + "\n")
        text = f"## CI cleanup validation: {report['status']}\n\nCommit: `{report['commit']}`\n\n"
        text += "\n".join(f"- {'PASS' if item['passed'] else 'FAIL'}: {item['name']}" for item in report["checks"])
        text += f"\n\nFixtures deleted: {report['fixtures_deleted']}. Non-fixture inventory unchanged: {report['non_fixture_inventory_unchanged']}.\n"
        text += "\nScope: empty disposable groups, an injected storage failure, and guarded cleanup. The main-workspace sweep is excluded.\n"
        if report["fixture_owner"] and not report["fixtures_deleted"]:
            text += f"\nRecovery selector: `{OWNER_TAG}={report['fixture_owner']}`. Verify ownership and contents before deletion.\n"
        (evidence / "summary.md").write_text(text)
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as stream:
                stream.write(text)
        print(text)
        return 0 if complete else 1


def guard_main():
    validation = Validation(os.environ["CLEANUP_VALIDATION_STATE"])
    try:
        return validation.guard(sys.argv[1:])
    except (ValidationError, KeyError, ValueError, OSError, subprocess.SubprocessError):
        validation.audit("refused")
        print("Validation refused an Azure operation. No raw Azure output is published.", file=sys.stderr)
        return 97


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("run", "cleanup", "summary"))
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--location", default="westeurope")
    args = parser.parse_args()
    validation = Validation(args.state_dir)
    try:
        if args.command == "summary":
            return validation.summary()
        if args.command == "cleanup":
            validation.cleanup_fixtures()
        else:
            validation.initialise(args.location)
            validation.scenarios()
            validation.cleanup_script(preview=True)
            validation.cleanup_script(preview=False)
            validation.state["status"] = "passed"
            validation.save()
        return 0
    except (ValidationError, KeyError, ValueError, OSError, subprocess.SubprocessError) as error:
        if validation.path.exists():
            validation.state["status"] = "incomplete" if isinstance(error, Incomplete) else "failed"
            validation.save()
        print(str(error) if isinstance(error, ValidationError) else "Validation failed before all checks completed.", file=sys.stderr)
        return 2 if isinstance(error, Incomplete) else 1


if __name__ == "__main__":
    sys.exit(main())

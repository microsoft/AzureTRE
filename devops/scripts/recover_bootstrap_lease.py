"""Recover only an empty, unowned bootstrap lease in an isolated PR CI backend."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

from ci_environment_id import environment_id


class RecoveryError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise RecoveryError(message)


def context():
    env = os.environ
    require(
        env.get("CI_BOOTSTRAP_LEASE_RECOVERY") == "true" and env.get("GITHUB_ACTIONS") == "true",
        "Bootstrap lease recovery is enabled only in PR GitHub Actions jobs.",
    )
    ref = env.get("TF_VAR_ci_git_ref", "")
    match = re.fullmatch(r"refs/pull/([1-9][0-9]*)/merge", ref)
    require(
        match is not None and match[1] == env.get("CI_RECOVERY_PR_NUMBER"),
        "The PR ownership reference does not match the event.",
    )
    repository = env.get("GITHUB_REPOSITORY", "")
    require(
        re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", repository)
        and repository.split("/")[-1] not in (".", ".."),
        "The GitHub repository is invalid.",
    )
    run_id = env.get("GITHUB_RUN_ID", "")
    attempt = env.get("GITHUB_RUN_ATTEMPT", "")
    require(
        run_id.isdecimal() and int(run_id) > 0 and attempt.isdecimal() and int(attempt) > 0,
        "The workflow run identity is missing.",
    )
    ref_id = hashlib.sha512((ref + "\n").encode()).hexdigest()[:8]
    regional_id = env.get("CI_ENVIRONMENT_ID", "")
    if regional_id:
        try:
            ref_id = environment_id(ref, env.get("TF_VAR_location", ""), env.get("AZURE_ENVIRONMENT", ""))
        except ValueError as error:
            raise RecoveryError(str(error)) from error
        require(regional_id == ref_id, "The regional CI environment identity does not match.")
    group = "rg-tre" + ref_id + "-mgmt"
    account = "tre" + ref_id + "mgmt"
    require(
        env.get("TF_VAR_mgmt_resource_group_name") == group and env.get("TF_VAR_mgmt_storage_account_name") == account,
        "The management account is not the expected isolated PR backend.",
    )
    subscription = env.get("ARM_SUBSCRIPTION_ID", "")
    require(re.fullmatch(r"[A-Za-z0-9-]+", subscription), "The Azure subscription is missing or invalid.")
    container = env.get("TF_VAR_terraform_state_container_name", "")
    require(re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", container), "The state container is invalid.")
    return {
        "ref": ref,
        "repository": repository,
        "run_id": int(run_id),
        "attempt": int(attempt),
        "group": group,
        "account": account,
        "subscription": subscription,
        "container": container,
    }


def azure(ctx, *args):
    result = subprocess.run(
        ["az", *args, "--subscription", ctx["subscription"], "--only-show-errors", "--output", "json"],
        capture_output=True,
        text=True,
        timeout=90,
    )
    require(result.returncode == 0, "Azure " + " ".join(args[:3]) + " failed: " + result.stderr.strip())
    try:
        return json.loads(result.stdout)
    except ValueError as error:
        raise RecoveryError("Azure returned invalid JSON.") from error


def verify_owner(ctx):
    group = azure(ctx, "group", "show", "--name", ctx["group"])
    expected = f"/subscriptions/{ctx['subscription']}/resourceGroups/{ctx['group']}"
    require(
        isinstance(group, dict) and isinstance(group.get("id"), str) and group["id"].lower() == expected.lower(),
        "The management resource group identity does not match.",
    )
    require(
        isinstance(group.get("tags"), dict) and group["tags"].get("ci_git_ref") == ctx["ref"],
        "The management resource group is not tagged for this PR.",
    )


def github(ctx, suffix):
    # The public repository's Actions API supports unauthenticated reads. This also
    # works before merge, when the reusable workflow on main has no actions:read grant.
    request = urllib.request.Request(
        "https://api.github.com/repos/" + ctx["repository"] + suffix,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "AzureTRE-bootstrap-lease-recovery",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310 - fixed https://api.github.com URL
            return json.load(response)
    except (urllib.error.URLError, ValueError) as error:
        raise RecoveryError("Could not verify workflow activity. No lease will be broken.") from error


def verify_workflows(ctx):
    current = github(ctx, f"/actions/runs/{ctx['run_id']}")
    require(
        isinstance(current, dict)
        and current.get("id") == ctx["run_id"]
        and current.get("run_attempt") == ctx["attempt"]
        and current.get("status") == "in_progress"
        and current.get("event") == "issue_comment"
        and current.get("path") == ".github/workflows/pr_comment_bot.yml"
        and isinstance(current.get("repository"), dict)
        and current["repository"].get("full_name") == ctx["repository"],
        "The current run is not an active PR comment workflow.",
    )
    workflow_prefix = ctx["repository"] + "/.github/workflows/deploy_tre_reusable.yml@"
    workflows = current.get("referenced_workflows")
    has_deployment = isinstance(workflows, list) and any(
        isinstance(item, dict) and isinstance(item.get("path"), str) and item["path"].startswith(workflow_prefix)
        for item in workflows
    )
    require(has_deployment, "The PR deployment workflow is not running.")
    # Comment workflows report main rather than the PR branch. Do not filter by
    # head_branch or pull_requests, or assume unrelated runs are harmless.
    for status in ("requested", "waiting", "pending", "queued", "in_progress"):
        seen = set()
        total = None
        for page in range(1, 12):
            data = github(ctx, f"/actions/runs?status={status}&per_page=100&page={page}")
            require(
                isinstance(data, dict)
                and type(data.get("total_count")) is int
                and isinstance(data.get("workflow_runs"), list),
                "GitHub returned incomplete workflow activity.",
            )
            require(0 <= data["total_count"] <= 1000, "The workflow activity list is too large to verify.")
            total = data["total_count"] if total is None else total
            require(total == data["total_count"], "Workflow activity changed during verification.")
            for run in data["workflow_runs"]:
                require(
                    isinstance(run, dict) and type(run.get("id")) is int and run["id"] not in seen,
                    "GitHub returned invalid workflow ownership data.",
                )
                seen.add(run["id"])
                require(run["id"] == ctx["run_id"], f"Another workflow is {status}. No lease will be broken.")
            require(len(seen) <= total, "GitHub returned inconsistent workflow activity.")
            if len(seen) == total:
                break
            require(len(data["workflow_runs"]) == 100, "GitHub omitted workflow activity.")
        else:
            raise RecoveryError("Could not verify all workflow activity.")
        if status == "in_progress":
            require(ctx["run_id"] in seen, "GitHub omitted the active recovery run.")


def blob(ctx, operation, *args):
    return azure(
        ctx,
        "storage",
        "blob",
        *operation,
        "--account-name",
        ctx["account"],
        "--container-name",
        ctx["container"],
        "--auth-mode",
        "login",
        *args,
    )


def snapshot(value):
    require(
        isinstance(value, dict) and value.get("name") == "bootstrap.tfstate",
        "The bootstrap blob identity does not match.",
    )
    properties = value.get("properties")
    metadata = value.get("metadata")
    require(
        isinstance(properties, dict)
        and isinstance(metadata, dict)
        and all(isinstance(k, str) and isinstance(v, str) for k, v in metadata.items()),
        "The bootstrap blob properties are incomplete.",
    )
    require(
        type(properties.get("contentLength")) is int and properties["contentLength"] == 0,
        "Populated bootstrap state requires manual recovery.",
    )
    require(properties.get("blobType") == "BlockBlob", "The bootstrap blob type is unexpected.")
    require(
        not any(key.lower() == "terraformlockid" and item for key, item in metadata.items()),
        "Terraform lock metadata requires manual recovery.",
    )
    require(
        isinstance(properties.get("etag"), str)
        and properties["etag"]
        and isinstance(properties.get("lastModified"), str)
        and properties["lastModified"],
        "The bootstrap blob version is missing.",
    )
    require(isinstance(properties.get("lease"), dict), "The bootstrap lease properties are missing.")
    return {
        "name": value["name"],
        "metadata": metadata,
        **{key: properties[key] for key in ("contentLength", "blobType", "etag", "lastModified")},
    }


def require_orphan(value):
    result = snapshot(value)
    require(
        value["properties"]["lease"] == {"duration": "infinite", "state": "leased", "status": "locked"},
        "Only an infinite, locked bootstrap lease can be recovered automatically.",
    )
    return result


def recover(ctx):
    verify_owner(ctx)
    account = azure(ctx, "storage", "account", "show", "--resource-group", ctx["group"], "--name", ctx["account"])
    expected = f"/subscriptions/{ctx['subscription']}/resourceGroups/{ctx['group']}/providers/Microsoft.Storage/storageAccounts/{ctx['account']}"
    require(
        isinstance(account, dict) and isinstance(account.get("id"), str) and account["id"].lower() == expected.lower(),
        "The storage account identity does not match.",
    )
    exists = blob(ctx, ["exists"], "--name", "bootstrap.tfstate")
    require(
        isinstance(exists, dict) and type(exists.get("exists")) is bool,
        "The bootstrap blob existence check is incomplete.",
    )
    if not exists["exists"]:
        print("Bootstrap state does not exist. No lease recovery is needed.")
        return
    initial = blob(ctx, ["show"], "--name", "bootstrap.tfstate")
    require(
        isinstance(initial, dict)
        and isinstance(initial.get("properties"), dict)
        and isinstance(initial["properties"].get("lease"), dict),
        "The bootstrap lease properties are incomplete.",
    )
    if initial["properties"]["lease"].get("status") == "unlocked":
        print("Bootstrap state is unlocked. No lease recovery is needed.")
        return
    before = require_orphan(initial)
    verify_workflows(ctx)
    print(
        "Eligible empty bootstrap lease found. Rechecking ownership and workflow activity in 10 seconds...", flush=True
    )
    time.sleep(10)
    verify_owner(ctx)
    current = blob(ctx, ["show"], "--name", "bootstrap.tfstate")
    require(require_orphan(current) == before, "The bootstrap blob changed. No lease will be broken.")
    verify_workflows(ctx)
    # The existing per-PR deployment concurrency group excludes other Terraform
    # writers. If-Match additionally rejects intervening content/metadata changes.
    # Lease operations do not change ETag or Last-Modified, so age is not ownership proof.
    print("Breaking the abandoned empty bootstrap lease once. Preserving blob content and metadata.", flush=True)
    blob(
        ctx,
        ["lease", "break"],
        "--blob-name",
        "bootstrap.tfstate",
        "--lease-break-period",
        "0",
        "--if-match",
        before["etag"],
    )
    after = blob(ctx, ["show"], "--name", "bootstrap.tfstate")
    require(
        snapshot(after) == before,
        "Bootstrap blob content or metadata changed during recovery. Terraform will not start.",
    )
    require(
        after["properties"]["lease"].get("status") == "unlocked"
        and after["properties"]["lease"].get("state") in ("available", "broken"),
        "The bootstrap lease is still locked. Terraform will not start.",
    )
    print("Bootstrap lease recovery verified. Terraform initialisation can proceed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("context", "verify-owner", "recover"))
    args = parser.parse_args()
    try:
        ctx = context()
        if args.operation == "verify-owner":
            verify_owner(ctx)
        elif args.operation == "recover":
            recover(ctx)
    except (RecoveryError, OSError, subprocess.TimeoutExpired) as error:
        print(f"ERROR: Bootstrap lease recovery refused: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

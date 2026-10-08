"""Destroy only CI environments tagged with an explicitly selected Git reference."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

from ci_environment_id import validate_ref


def azure(subscription, *args):
    # The existing destroy helper uses the default account. Verify that default,
    # rather than selecting the requested account for this identity check.
    subscription_args = [] if args == ("account", "show") else ["--subscription", subscription]
    result = subprocess.run(["az", *args, *subscription_args, "--only-show-errors", "--output", "json"],
                            capture_output=True, text=True, timeout=90, check=True)
    return json.loads(result.stdout)


def targets(groups, ref, subscription):
    if not isinstance(groups, list):
        raise ValueError("Azure returned an incomplete resource group inventory.")
    inventory = {}
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("name"), str) or group["name"].lower() in inventory:
            raise ValueError("Azure returned an invalid resource group inventory.")
        if group.get("tags") is not None and not isinstance(group["tags"], dict):
            raise ValueError("Azure returned invalid resource group tags.")
        inventory[group["name"].lower()] = group
    selected = set()
    for name, group in inventory.items():
        if not re.fullmatch(r"rg-tre[0-9a-f]{8}(-mgmt)?", name) or (group.get("tags") or {}).get("ci_git_ref") != ref:
            continue
        core = name.removesuffix("-mgmt")
        for sibling in (core, core + "-mgmt"):
            if sibling in inventory:
                value = inventory[sibling]
                expected = f"/subscriptions/{subscription}/resourceGroups/{sibling}"
                if not isinstance(value.get("id"), str) or value["id"].lower() != expected.lower():
                    raise ValueError("The CI resource group identity does not match.")
                if (value.get("tags") or {}).get("ci_git_ref") != ref:
                    raise ValueError("Core and management group ownership differs. Cleanup stopped.")
        selected.add(core)
    return sorted(selected)


def verify_account(subscription):
    account = azure(subscription, "account", "show")
    if not isinstance(account, dict) or not isinstance(account.get("id"), str) or account["id"].lower() != subscription.lower():
        raise ValueError("The default Azure subscription does not match. Cleanup stopped.")


def destroy(ref, subscription):
    validate_ref(ref)
    if not re.fullmatch(r"[A-Za-z0-9-]+", subscription):
        raise ValueError("The Azure subscription is missing or invalid.")
    verify_account(subscription)
    groups = targets(azure(subscription, "group", "list"), ref, subscription)
    if not groups:
        print("No CI environments found for the selected reference.")
    for group in groups:
        # The caller holds the deployment concurrency group for this reference.
        # Recheck ownership immediately before invoking the existing destroy helper.
        inventory = azure(subscription, "group", "list")
        if group not in targets(inventory, ref, subscription):
            raise ValueError("CI resource group ownership changed. Cleanup stopped.")
        names = {row["name"].lower() for row in inventory}
        current = [azure(subscription, "group", "show", "--name", name)
                   for name in (group, group + "-mgmt") if name in names]
        if targets(current, ref, subscription) != [group]:
            raise ValueError("CI resource group ownership changed. Cleanup stopped.")
        verify_account(subscription)
        print("Destroying CI environment " + group, flush=True)
        subprocess.run(["bash", str(Path(__file__).with_name("destroy_env_no_terraform.sh")), "--core-tre-rg", group], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--subscription", required=True)
    args = parser.parse_args()
    try:
        destroy(args.ref, args.subscription)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"ERROR: CI environment cleanup refused: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

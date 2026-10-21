"""Name isolated CI environments by Git reference, Azure cloud and location."""

import argparse
import hashlib
import json
import os
import re

DEFAULT_PREFIX = "tre"
DEFAULT_PREFIX_REPOSITORY = "microsoft/AzureTRE"
REPOSITORY_TAG = "ci_repository"


def environment_prefix(value=None):
    """Return the CI name prefix. A fork sets CI_ENV_PREFIX to keep its groups apart."""
    configured = os.environ.get("CI_ENV_PREFIX", "") if value is None else value
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    # Fail closed: a fork that forgot the prefix would share names with the upstream CI.
    # A fork that must keep its existing environment names sets CI_ENV_PREFIX to "tre" explicitly.
    if not configured and repository and repository.lower() != DEFAULT_PREFIX_REPOSITORY.lower():
        raise ValueError("Set the CI_ENV_PREFIX repository variable. Only the upstream repository has a default.")
    prefix = configured or DEFAULT_PREFIX
    # The prefix and the 8-character hash fill the 11-character tre_id limit.
    if not re.fullmatch(r"[a-z][a-z0-9]{2}", prefix):
        raise ValueError("The CI environment prefix must be 3 lowercase letters or digits, starting with a letter.")
    return prefix


def ci_tags(tags):
    """Return the tags with lowercase names, because Azure tag names are not case-sensitive."""
    result = {name.lower(): value for name, value in (tags or {}).items()}
    if len(result) != len(tags or {}):
        raise ValueError("Tag names differ only in case.")
    return result


def repository_owns(tags, repository, prefix=None):
    """Refuse groups that another repository tagged. Groups from before the tag carry no owner."""
    owner = ci_tags(tags).get(REPOSITORY_TAG)
    if owner is None:
        # Before the tag existed, only the upstream CI created groups with the default prefix.
        prefix = environment_prefix() if prefix is None else prefix
        return prefix != DEFAULT_PREFIX or repository.lower() == DEFAULT_PREFIX_REPOSITORY.lower()
    return isinstance(owner, str) and owner.lower() == repository.lower()


def validate_ref(ref):
    if not re.fullmatch(r"refs/(pull/[1-9][0-9]*/merge|heads/.+)", ref) or ref == "refs/heads/main":
        raise ValueError("Use a PR merge reference or a non-main branch reference.")
    if re.search(r"[ ~^:?*\[\\\x00-\x20\x7f]", ref) or any(item in ref for item in ("..", "//", "@{")):
        raise ValueError("The CI Git reference is invalid.")
    if any(part.startswith(".") or part.endswith((".", ".lock")) for part in ref.split("/")) or ref.endswith("/"):
        raise ValueError("The CI Git reference is invalid.")


def environment_id(ref, location, cloud="AzureCloud"):
    validate_ref(ref)
    location = location.replace(" ", "").lower()
    if not re.fullmatch(r"[a-z][a-z0-9]+", location):
        raise ValueError("The CI Azure location is missing or invalid.")
    cloud = (cloud or "AzureCloud").lower()
    if cloud not in ("azurecloud", "azureusgovernment", "azurechinacloud", "azuregermancloud"):
        raise ValueError("The CI Azure cloud is invalid.")
    identity = json.dumps(["AzureTRE-CI-v1", ref, cloud, location], separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha512(identity.encode()).hexdigest()[:8]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--location", required=True)
    parser.add_argument("--cloud", default="AzureCloud")
    parser.add_argument("--with-prefix", action="store_true", help="Print the TRE ID, including CI_ENV_PREFIX.")
    args = parser.parse_args()
    try:
        ref_id = environment_id(args.ref, args.location, args.cloud)
        print(environment_prefix() + ref_id if args.with_prefix else ref_id)
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()

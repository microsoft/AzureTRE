"""Name isolated CI environments by Git reference, Azure cloud and location."""

import argparse
import hashlib
import json
import re


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
    args = parser.parse_args()
    try:
        print(environment_id(args.ref, args.location, args.cloud))
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()

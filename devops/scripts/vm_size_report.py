"""Report the VM sizes that the repository references and their availability in Azure regions.

Examples:
    python3 devops/scripts/vm_size_report.py --region switzerlandnorth
    python3 devops/scripts/vm_size_report.py --region switzerlandnorth,uksouth --output vm-size-report.md
    python3 devops/scripts/vm_size_report.py                      # no Azure login: catalogue check only
    python3 devops/scripts/vm_size_report.py --refresh-catalogue  # rewrite the catalogue of all VM sizes
"""

import argparse
from collections import Counter, namedtuple
import datetime
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import quote

SCRIPT = Path(__file__).resolve()
CATALOGUE = SCRIPT.with_name("vm_size_catalogue.txt")
# The scan skips the files of this tool. The catalogue lists all sizes, and the tests and the docs page use
# example sizes.
OWN_FILES = {
    SCRIPT,
    CATALOGUE,
    SCRIPT.parents[1] / "tests" / "test_vm_size_report.py",
    SCRIPT.parents[2] / "docs" / "tre-admins" / "vm-size-availability.md",
}
# After the prefix, a VM size has a family of letters and a vCPU count, in any case.
# The vCPU count keeps out Standard_LRS and identifiers such as basic_workspace_request. A tier such as
# Standard_v2 is not a VM size. The word boundary keeps out database SKUs such as GP_Standard_D2ds_v4.
VM_SIZE = re.compile(r"\b(?i:standard|basic)_(?![vV][0-9]+\b)[A-Za-z]+[0-9][A-Za-z0-9_-]*")
# A database tier label such as "B | 4GB 2vCores" can map to a database SKU without its tier prefix, for example
# {"B | 4GB 2vCores": "Standard_B2s"}. The scan skips a size that is the value of such a label, because it is
# a database SKU and not a VM size.
DATABASE_TIER_KEY = re.compile(r'"[A-Z]{1,2} \| \d+GB \d+vCores"\s*[:=]\s*"$')
REGION = re.compile(r"[a-z0-9]+")
# Keep only the fields that the report uses. The full output for all regions is too large.
SKU_FIELDS = (
    "[].{name: name, location: locations[0], restrictions: restrictions, "
    "vCPUs: capabilities[?name=='vCPUs'].value | [0], memoryGB: capabilities[?name=='MemoryGB'].value | [0]}"
)
# Azure ML has its own list of sizes for each region, and does not use the VM restrictions of the subscription.
AML_API_VERSION = "2025-04-01"
AML_FIELDS = "value[].{name: name, vCPUs: vCPUs, memoryGB: memoryGB, computeTypes: supportedComputeTypes}"
# The services that use the sizes. The Azure ML keys are compute types.
SERVICES = {"vm": "VM", "AmlCompute": "AML cluster", "ComputeInstance": "AML instance"}
Reference = namedtuple("Reference", "path line size")
# The report shows the categories in this order, so that problems come first.
CATEGORIES = {
    "unknown": (
        "❓",
        "Unknown name",
        "The name is not in the Azure catalogue. The size is retired or the name is wrong.",
    ),
    "blocked": ("⛔", "Blocked", "The region has the size, but the subscription cannot use it."),
    "not offered": ("❌", "Not offered", "The region does not have the size for this service."),
    "zones blocked": ("⚠️", "Some zones blocked", "The subscription can use the size, but not in the zones shown."),
    "not checked": ("➖", "Not checked", "The script could not get the Azure ML sizes of the region."),
    "available": ("✅", "Available", "The subscription can use the size in the region."),
    "listed": ("✔️", "In catalogue", "The name is in the Azure catalogue. No region was checked."),
}
KINDS = ("code", "sample", "test", "docs")


def az(args, subscription=None):
    """Run an Azure CLI command and return its JSON output."""
    command = ["az", *args, "--output", "json"]
    if subscription:
        command += ["--subscription", subscription]
    return json.loads(subprocess.run(command, check=True, capture_output=True, text=True).stdout)


def list_skus(region=None, subscription=None):
    """Return the VM SKUs of one region, or of all regions. The restrictions apply to the subscription."""
    location = ["--location", region] if region else []
    return az(
        ["vm", "list-skus", *location, "--resource-type", "virtualMachines", "--all", "--query", SKU_FIELDS],
        subscription,
    )


def region_skus(regions, subscription=None):
    """Return the SKUs of each region by lowercase name. One query for all regions is faster than one per region."""
    skus = list_skus(regions[0] if len(regions) == 1 else None, subscription)
    result = {region: {} for region in regions}
    for sku in skus:
        location = (sku.get("location") or "").lower()
        if location in result:
            result[location][sku["name"].lower()] = sku
    return result


def aml_sizes(region, subscription_id):
    """Return the Azure ML sizes of a region by lowercase name, or None if Azure ML does not answer."""
    url = f"/subscriptions/{subscription_id}/providers/Microsoft.MachineLearningServices/locations/{region}/vmSizes"
    try:
        sizes = az(["rest", "--method", "get", "--url", f"{url}?api-version={AML_API_VERSION}", "--query", AML_FIELDS])
    except subprocess.CalledProcessError as error:
        message = (error.stderr or "").strip()[:300]
        print(f"Warning: the script could not get the Azure ML sizes of {region}: {message}", file=sys.stderr)
        return None
    return {size["name"].lower(): size for size in sizes}


def parse_regions(values):
    """Return the regions from values such as "Switzerland North, uksouth", in order and without duplicates."""
    regions = []
    for value in values:
        for item in value.split(","):
            region = item.replace(" ", "").lower()
            if region and region not in regions:
                if not REGION.fullmatch(region):
                    raise ValueError(f"{item.strip()!r} is not an Azure region name.")
                regions.append(region)
    return regions


def refresh_catalogue(path, subscription=None):
    """Write the names of the VM sizes that Azure lists in all regions, and return the number of names."""
    names = sorted({sku["name"] for sku in list_skus(subscription=subscription)}, key=str.lower)
    if not names:
        raise ValueError("Azure listed no VM sizes. The catalogue did not change.")
    today = datetime.date.today().isoformat()
    header = (
        f"# VM sizes that Azure listed in all regions on {today}. Refresh with: vm_size_report.py --refresh-catalogue\n"
    )
    path.write_text(header + "\n".join(names) + "\n", encoding="utf-8")
    return len(names)


def read_catalogue(path):
    """Return the refresh date of the catalogue, and a map from the lowercase name to the name."""
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    date = re.search(r"\d{4}-\d{2}-\d{2}", next((line for line in lines if line.startswith("#")), ""))
    return (date.group() if date else None), {line.lower(): line for line in lines if line and not line.startswith("#")}


def reference_kind(path):
    """Return the kind of file, so that the report can separate deployed values from examples."""
    parts = Path(path).parts
    if parts[0] == "e2e_tests" or parts[-1].startswith("test_") or any(part.startswith("tests") for part in parts[:-1]):
        return "test"
    if parts[0] == "api_http_requests" or ".sample" in parts[-1]:
        return "sample"
    if parts[0] == "docs" or parts[-1].endswith(".md"):
        return "docs"
    return "code"


def reference_service(path):
    """Return the service that uses the sizes in a file: "vm", or the Azure ML compute type."""
    parts = Path(path).parts
    if "aml_compute" in parts or re.search(r"(^|_)aml[._]", parts[-1]):
        return "ComputeInstance"
    if "azureml" in parts:
        return "AmlCompute"
    return "vm"


def find_references(repo, exclude=()):
    """Return the VM size references in the tracked text files, by lowercase size name."""
    files = subprocess.run(["git", "-C", str(repo), "ls-files", "-z"], check=True, capture_output=True, text=True)
    references = {}
    for name in filter(None, files.stdout.split("\0")):
        path = repo / name
        # Git also tracks the target of a symlink, so a symlink would only give duplicate references.
        if path.is_symlink() or not path.is_file() or path.resolve() in exclude:
            continue
        data = path.read_bytes()
        if b"\0" in data:
            continue
        # Split on newlines only, so that the line numbers are the same as on GitHub.
        for number, line in enumerate(data.decode("utf-8", errors="replace").split("\n"), start=1):
            for match in VM_SIZE.finditer(line):
                if DATABASE_TIER_KEY.search(line, 0, match.start()):
                    continue
                size = match.group().rstrip("_-")
                references.setdefault(size.lower(), []).append(Reference(name, number, size))
    return references


def region_status(sku):
    """Return the category and the cell text of a size that the region lists."""
    restrictions = sku.get("restrictions") or []
    if any(item["type"] == "Location" for item in restrictions):
        return "blocked", "blocked"
    zones = sorted(
        {
            zone
            for item in restrictions
            if item["type"] == "Zone"
            for zone in (item.get("restrictionInfo") or {}).get("zones") or []
        }
    )
    if zones:
        return "zones blocked", f"{'zone' if len(zones) == 1 else 'zones'} {', '.join(zones)} blocked"
    return "available", "available"


def size_status(key, skus, catalogue):
    """Return the category and the cell text of a size. If skus is None, use only the catalogue."""
    if skus is not None and key in skus:
        return region_status(skus[key])
    if key not in catalogue:
        return "unknown", "unknown name"
    if skus is None:
        return "listed", "in catalogue"
    return "not offered", "not offered"


def aml_status(key, sizes, compute_type, catalogue):
    """Return the category and the cell text of a size for an Azure ML compute type in a region."""
    if key not in catalogue:
        return "unknown", "unknown name"
    if sizes is None:
        return "not checked", "not checked"
    compute_types = (sizes.get(key) or {}).get("computeTypes") or []
    if compute_type in compute_types:
        return "available", "available"
    return "not offered", "not offered"


def cell(status):
    category, text = status
    return f"{CATEGORIES[category][0]} {text}"


def number(value):
    """Return a number as the VM SKU list shows it, for example 7 and not 7.0."""
    return f"{value:g}" if isinstance(value, float) else str(value or "")


def render(references, catalogue, regions=None, skus=None, aml=None, account=None, catalogue_date=None, link_base=None):
    """Return the report as Markdown. Without regions, the report checks the names against the catalogue only."""
    columns = regions or ["catalogue"]
    # A size that a region lists is real, even if the catalogue is older than the size.
    known = dict(catalogue)
    for region_data in [*(skus or {}).values(), *(aml or {}).values()]:
        known.update({key: size["name"] for key, size in (region_data or {}).items()})

    # A size gets one row for each service that uses it, because Azure ML has its own list of sizes.
    groups = {}
    for key, refs in references.items():
        for ref in refs:
            groups.setdefault((key, reference_service(ref.path)), []).append(ref)

    entries = []
    for (key, service), refs in groups.items():
        if regions and service != "vm":
            sources = [(aml or {}).get(region) for region in regions]
            statuses = [aml_status(key, source, service, known) for source in sources]
        else:
            sources = [skus[region] for region in regions] if regions else [None]
            statuses = [size_status(key, source, known) for source in sources]
        size = next((source[key] for source in sources if source and key in source), None)
        name = known.get(key, refs[0].size)
        kinds = Counter(reference_kind(ref.path) for ref in refs)
        worst = min(list(CATEGORIES).index(category) for category, _ in statuses)
        order = (worst, "code" not in kinds, name.lower(), list(SERVICES).index(service))
        entries.append((order, name, SERVICES[service], statuses, size, kinds, refs))
    entries.sort(key=lambda entry: entry[0])

    lines = ["# VM size availability" if regions else "# VM sizes in the repository", ""]
    if regions:
        lines.append(f"- Regions: {', '.join(regions)}")
    if account:
        lines.append(f"- Subscription: {account['name']}")
    refreshed = f", refreshed {catalogue_date}" if catalogue_date else ""
    places = sum(len(refs) for refs in references.values())
    lines += [
        f"- Date: {datetime.date.today().isoformat()}",
        f"- Catalogue: {len(catalogue)} VM sizes{refreshed}",
        f"- Referenced VM sizes: {len(references)}, in {places} places",
        "",
        "| Status | " + " | ".join(columns) + " |",
        "| --- |" + " --- |" * len(columns),
    ]
    counts = [Counter(entry[3][index][0] for entry in entries) for index in range(len(columns))]
    for category, (icon, label, _) in CATEGORIES.items():
        if any(count[category] for count in counts):
            lines.append(f"| {icon} {label} | " + " | ".join(str(count[category]) for count in counts) + " |")

    size_columns = ["vCPUs", "Memory (GB)"] if regions else []
    header = ["VM size", "Service", *size_columns, *columns, "References"]
    lines += ["", "| " + " | ".join(header) + " |", "|" + " --- |" * len(header)]
    for _, name, service, statuses, size, kinds, _ in entries:
        sizes = [number((size or {}).get("vCPUs")), number((size or {}).get("memoryGB"))] if regions else []
        summary = ", ".join(f"{kind} {kinds[kind]}" for kind in KINDS if kinds[kind])
        lines.append("| " + " | ".join([f"`{name}`", service, *sizes, *map(cell, statuses), summary]) + " |")

    used = {category for count in counts for category in count}
    lines += ["", "Status key:", ""]
    lines += [
        f"- {icon} **{label}**: {meaning}"
        for category, (icon, label, meaning) in CATEGORIES.items()
        if category in used
    ]
    if regions and any(entry[2] != SERVICES["vm"] for entry in entries):
        lines += [
            "",
            "AML rows use the Azure ML list of sizes for the region and the compute type. "
            "Azure ML does not use the VM restrictions of the subscription.",
        ]
    lines += ["", "<details>", f"<summary>References for {len(references)} VM sizes</summary>"]
    for _, name, service, _, _, _, refs in entries:
        lines += ["", f"### `{name}` ({service})", ""]
        for ref in refs:
            location = f"`{ref.path}:{ref.line}`"
            if link_base:
                location = f"[{location}]({link_base.rstrip('/')}/{quote(ref.path)}#L{ref.line})"
            lines.append(f"- {location} ({reference_kind(ref.path)})")
    lines += ["", "</details>"]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--region",
        action="append",
        default=[],
        help="Azure region, for example switzerlandnorth. Separate more regions with commas, or give the option "
        "again. If you do not give a region, the script checks the names against the catalogue only.",
    )
    parser.add_argument("--subscription", help="Subscription name or ID. The default is the Azure CLI subscription.")
    parser.add_argument(
        "--hide-subscription",
        action="store_true",
        help="Do not put the subscription name in the report, for example in a public CI artifact.",
    )
    parser.add_argument("--repo", type=Path, default=SCRIPT.parents[2], help="Repository root.")
    parser.add_argument("--catalogue", type=Path, default=CATALOGUE, help="File with the names of all VM sizes.")
    parser.add_argument("--output", type=Path, help="Write the Markdown report to this file.")
    parser.add_argument("--link-base", help="URL that the report puts in front of each file path, to make links.")
    parser.add_argument(
        "--refresh-catalogue",
        action="store_true",
        help="Query all regions, write the catalogue and stop. This takes about 1.5 minutes.",
    )
    args = parser.parse_args(argv)
    try:
        regions = parse_regions(args.region)
    except ValueError as error:
        parser.error(str(error))
    if args.region and not regions:
        parser.error("--region has no region name.")

    skus = aml = account = None
    try:
        if args.refresh_catalogue:
            count = refresh_catalogue(args.catalogue, args.subscription)
            print(f"Wrote {count} VM sizes to {args.catalogue}", file=sys.stderr)
            return
        catalogue_date, catalogue = read_catalogue(args.catalogue)
        # With --repo, the scan also skips the tool files at the same paths in that repository.
        own_files = OWN_FILES | {
            (args.repo / path.relative_to(SCRIPT.parents[2])).resolve()
            for path in OWN_FILES
            if path.is_relative_to(SCRIPT.parents[2])
        }
        references = find_references(args.repo, own_files | {args.catalogue.resolve()})
        if regions:
            skus = region_skus(regions, args.subscription)
            empty = [region for region in regions if not skus[region]]
            if empty:
                sys.exit(f"Azure lists no VM sizes in {', '.join(empty)}. Check the region names.")
            account = az(["account", "show"], args.subscription)
            if any(reference_service(ref.path) != "vm" for refs in references.values() for ref in refs):
                aml = {region: aml_sizes(region, account["id"]) for region in regions}
    except subprocess.CalledProcessError as error:
        sys.exit(f"{error.cmd[0]} failed: {(error.stderr or '').strip()}")
    except (OSError, ValueError) as error:
        sys.exit(str(error))

    shown_account = None if args.hide_subscription else account
    report = render(references, catalogue, regions, skus, aml, shown_account, catalogue_date, args.link_base)
    if args.output:
        args.output.write_text(report, encoding="utf-8")
    else:
        sys.stdout.write(report)


if __name__ == "__main__":
    main()

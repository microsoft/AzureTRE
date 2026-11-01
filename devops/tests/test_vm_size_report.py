"""Find the VM sizes in the repository and report their availability in Azure regions."""

import datetime
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import vm_size_report  # noqa: E402
from vm_size_report import (  # noqa: E402
    CATALOGUE,
    OWN_FILES,
    VM_SIZE,
    Reference,
    find_references,
    parse_regions,
    read_catalogue,
    reference_kind,
    reference_service,
    refresh_catalogue,
    region_skus,
    size_status,
)


def sku(name, location="switzerlandnorth", *restrictions):
    return {"name": name, "location": location, "restrictions": list(restrictions), "vCPUs": "2", "memoryGB": "4"}


def git_repo(directory, files):
    repo = Path(directory)
    for name, content in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", *files], check=True)
    return repo


def table_rows(report):
    return [
        [cell.strip() for cell in line.strip("|").split("|")] for line in report.splitlines() if line.startswith("| `")
    ]


class PatternTests(unittest.TestCase):
    def test_finds_vm_sizes_in_any_case(self):
        line = 'sizes = ["Standard_B2s", "STANDARD_D2_V3", "Standard_E64-32s_v5", "Basic_A0"]'
        self.assertEqual(
            [match.group() for match in VM_SIZE.finditer(line)],
            ["Standard_B2s", "STANDARD_D2_V3", "Standard_E64-32s_v5", "Basic_A0"],
        )

    def test_skips_skus_that_are_not_vm_sizes(self):
        line = (
            "Standard_LRS Standard_GRS Standard_v2 basic_workspace_request basic_resource_template "
            "GP_Standard_D2ds_v4 B_Standard_B1ms MO_Standard_E2ds_v4"
        )
        self.assertEqual(list(VM_SIZE.finditer(line)), [])


class RegionTests(unittest.TestCase):
    def test_accepts_display_names_lists_and_repeated_options(self):
        self.assertEqual(
            parse_regions(["Switzerland North, uksouth", "UKSouth,,eastus2 "]),
            ["switzerlandnorth", "uksouth", "eastus2"],
        )

    def test_rejects_names_that_are_not_regions(self):
        for value in ("uk-south", "eastus;whoami", "$(id)"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_regions([value])

    def test_one_region_uses_a_location_filter(self):
        with patch.object(vm_size_report, "az", return_value=[sku("Standard_B2s")]) as az:
            result = region_skus(["switzerlandnorth"])
        self.assertIn("--location", az.call_args.args[0])
        self.assertEqual(list(result["switzerlandnorth"]), ["standard_b2s"])

    def test_more_regions_use_one_query_and_ignore_the_case_of_locations(self):
        skus = [sku("Standard_B2s", "SwitzerlandNorth"), sku("Standard_B2s", "uksouth"), sku("Standard_B2s", "eastus")]
        with patch.object(vm_size_report, "az", return_value=skus) as az:
            result = region_skus(["switzerlandnorth", "uksouth"])
        self.assertEqual(az.call_count, 1)
        self.assertNotIn("--location", az.call_args.args[0])
        self.assertEqual(
            {region: list(data) for region, data in result.items()},
            {"switzerlandnorth": ["standard_b2s"], "uksouth": ["standard_b2s"]},
        )


class StatusTests(unittest.TestCase):
    catalogue = {"standard_b2s": "Standard_B2s", "standard_d4s_v5": "Standard_D4s_v5"}

    def test_location_restriction_blocks_the_size(self):
        restrictions = ({"type": "Location"}, {"type": "Zone", "restrictionInfo": {"zones": ["1", "2", "3"]}})
        skus = {"standard_b2s": sku("Standard_B2s", "switzerlandnorth", *restrictions)}
        self.assertEqual(size_status("standard_b2s", skus, self.catalogue), ("blocked", "blocked"))

    def test_zone_restriction_names_the_zones(self):
        restriction = {"type": "Zone", "restrictionInfo": {"zones": ["3", "1"]}}
        skus = {"standard_b2s": sku("Standard_B2s", "switzerlandnorth", restriction)}
        self.assertEqual(size_status("standard_b2s", skus, self.catalogue), ("zones blocked", "zones 1, 3 blocked"))

    def test_size_without_restrictions_is_available(self):
        skus = {"standard_b2s": sku("Standard_B2s")}
        self.assertEqual(size_status("standard_b2s", skus, self.catalogue), ("available", "available"))

    def test_catalogue_separates_regional_gaps_from_wrong_names(self):
        self.assertEqual(size_status("standard_d4s_v5", {}, self.catalogue), ("not offered", "not offered"))
        self.assertEqual(size_status("standard_ds2_v3", {}, self.catalogue), ("unknown", "unknown name"))

    def test_without_a_region_the_catalogue_decides(self):
        self.assertEqual(size_status("standard_b2s", None, self.catalogue)[0], "listed")
        self.assertEqual(size_status("standard_a1", None, self.catalogue)[0], "unknown")


class ScanTests(unittest.TestCase):
    def test_reference_kind_separates_deployed_values_from_examples(self):
        cases = {
            "core/terraform/variables.tf": "code",
            "templates/shared_services/admin-vm/template_schema.json": "code",
            "e2e_tests/resources/aml.py": "test",
            "api_app/tests_ma/test_services/test_schema_service.py": "test",
            "devops/tests/test_bootstrap.py": "test",
            "config.sample.yaml": "sample",
            "templates/workspace_services/azureml/user_resources/aml_compute/.env.sample": "sample",
            "api_http_requests/API User Journey.http": "sample",
            "docs/tre-admins/environment-variables.md": "docs",
            "CHANGELOG.md": "docs",
        }
        self.assertEqual({path: reference_kind(path) for path in cases}, cases)

    def test_scans_each_tracked_text_file_once_with_github_line_numbers(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = git_repo(
                directory,
                {
                    "main.tf": 'size = "Standard_B2s"\n\nsku = "STANDARD_B2S"\n',
                    "catalogue.txt": "Standard_B2s\nStandard_D4s_v5\n",
                    "image.png": b"\x89PNG\r\n\x1a\n\0\0Standard_D4s_v5",
                    # Not UTF-8, and a form feed that GitHub does not count as a new line.
                    "latin1.tf": b'# caf\xe9\fend\nsize = "Standard_D2s_v5"\n',
                },
            )
            (repo / "link.tf").symlink_to("main.tf")
            subprocess.run(["git", "-C", str(repo), "add", "link.tf"], check=True)
            (repo / "untracked.tf").write_text('size = "Standard_D8s_v5"\n')
            references = find_references(repo, {(repo / "catalogue.txt").resolve()})
        self.assertEqual(
            references,
            {
                "standard_b2s": [Reference("main.tf", 1, "Standard_B2s"), Reference("main.tf", 3, "STANDARD_B2S")],
                "standard_d2s_v5": [Reference("latin1.tf", 2, "Standard_D2s_v5")],
            },
        )

    def test_scan_skips_database_skus_that_a_tier_label_maps(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = git_repo(
                directory,
                {
                    "test_mysql.py": (
                        'SKUS = {"B | 4GB 2vCores": "Standard_B2s", "GP | 8GB 2vCores": "Standard_D2ds_v4"}\n'
                        'VM = {"vm_size": "Standard_B2s"}\n'
                        'PAYLOAD = {"sql_sku": "B | 4GB 2vCores", "vm_size": "Standard_D2s_v5"}\n'
                    ),
                    "locals.tf": '"BC | 16GB 2vCores" = "Standard_E2ds_v4"\n',
                },
            )
            references = find_references(repo)
        self.assertEqual(
            references,
            {
                "standard_b2s": [Reference("test_mysql.py", 2, "Standard_B2s")],
                "standard_d2s_v5": [Reference("test_mysql.py", 3, "Standard_D2s_v5")],
            },
        )

    def test_scan_skips_the_files_of_this_tool(self):
        self.assertIn(Path(__file__).resolve(), OWN_FILES)
        self.assertTrue(all(path.is_file() for path in OWN_FILES))


class ServiceTests(unittest.TestCase):
    def test_azure_ml_files_use_the_azure_ml_compute_type(self):
        cases = {
            "templates/workspace_services/azureml/terraform/compute.tf": "AmlCompute",
            "templates/workspace_services/azureml/user_resources/aml_compute/porter.yaml": "ComputeInstance",
            "e2e_tests/resources/aml.py": "ComputeInstance",
            "e2e_tests/unit_tests/test_aml_lifecycle.py": "ComputeInstance",
            "templates/shared_services/sonatype-nexus-vm/porter.yaml": "vm",
            "e2e_tests/resources/nexus.py": "vm",
            "templates/workspace_services/guacamole/user_resources/guacamole-azure-windowsvm/porter.yaml": "vm",
        }
        self.assertEqual({path: reference_service(path) for path in cases}, cases)


class AzureMlReportTests(unittest.TestCase):
    files = {
        "templates/workspace_services/azureml/terraform/compute.tf": 'vmSize = "Standard_DS2_v2"\n',
        "templates/workspace_services/azureml/user_resources/aml_compute/porter.yaml": (
            'default: "Standard_D2_v3"\nother: "Standard_B2s"\n'
        ),
        "templates/shared_services/admin-vm/porter.yaml": 'default: "Standard_DS2_v2"\n',
        "catalogue.txt": "Standard_B2s\nStandard_D2_v3\nStandard_DS2_v2\n",
    }

    def run_report(self, aml_error=None):
        def fake_az(command, subscription=None):
            if command[0] == "account":
                return {"name": "Test subscription", "id": "0000"}
            if command[0] == "rest":
                if aml_error:
                    raise aml_error
                return [
                    {"name": "Standard_DS2_v2", "vCPUs": 2, "memoryGB": 7.0, "computeTypes": ["AmlCompute"]},
                    {"name": "Standard_D2_v3", "vCPUs": 2, "memoryGB": 8.0, "computeTypes": ["ComputeInstance"]},
                ]
            return [
                sku("Standard_DS2_v2", "switzerlandnorth", {"type": "Location"}),
                sku("Standard_B2s"),
                sku("Standard_D2_v3"),
            ]

        with tempfile.TemporaryDirectory() as directory:
            repo = git_repo(directory, self.files)
            with (
                patch.object(vm_size_report, "az", side_effect=fake_az) as az,
                patch("sys.stdout", new_callable=io.StringIO) as output,
                patch("sys.stderr", new_callable=io.StringIO) as errors,
            ):
                vm_size_report.main(
                    ["--region", "switzerlandnorth", "--repo", str(repo), "--catalogue", str(repo / "catalogue.txt")]
                )
        return output.getvalue(), errors.getvalue(), az

    def test_azure_ml_rows_use_the_azure_ml_list_of_sizes(self):
        report, _, az = self.run_report()
        self.assertIn(
            "/subscriptions/0000/providers/Microsoft.MachineLearningServices/locations/switzerlandnorth/",
            az.call_args_list[-1].args[0][4],
        )
        self.assertEqual(
            [[row[0], row[1], row[2], row[3], row[4]] for row in table_rows(report)],
            [
                ["`Standard_DS2_v2`", "VM", "2", "4", "⛔ blocked"],
                ["`Standard_B2s`", "AML instance", "", "", "❌ not offered"],
                ["`Standard_D2_v3`", "AML instance", "2", "8", "✅ available"],
                ["`Standard_DS2_v2`", "AML cluster", "2", "7", "✅ available"],
            ],
        )
        self.assertIn("### `Standard_DS2_v2` (AML cluster)", report)

    def test_azure_ml_error_marks_the_rows_not_checked(self):
        error = subprocess.CalledProcessError(1, ["az", "rest"], stderr="ERROR: NoRegisteredProviderFound\n")
        report, errors, _ = self.run_report(aml_error=error)
        self.assertIn("could not get the Azure ML sizes of switzerlandnorth: ERROR: NoRegisteredProviderFound", errors)
        self.assertEqual(
            [[row[0], row[1], row[4]] for row in table_rows(report)],
            [
                ["`Standard_DS2_v2`", "VM", "⛔ blocked"],
                ["`Standard_B2s`", "AML instance", "➖ not checked"],
                ["`Standard_D2_v3`", "AML instance", "➖ not checked"],
                ["`Standard_DS2_v2`", "AML cluster", "➖ not checked"],
            ],
        )


class CatalogueTests(unittest.TestCase):
    def test_catalogue_gives_the_refresh_date_and_the_names(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalogue.txt"
            path.write_text("# VM sizes that Azure listed in all regions on 2026-10-23.\nStandard_B2s\n\n")
            self.assertEqual(read_catalogue(path), ("2026-10-23", {"standard_b2s": "Standard_B2s"}))

    def test_every_catalogue_name_matches_the_pattern(self):
        _, names = read_catalogue(CATALOGUE)
        self.assertGreater(len(names), 1000)
        self.assertEqual([name for name in names.values() if not VM_SIZE.fullmatch(name)], [])

    def test_refresh_writes_a_catalogue_that_read_catalogue_reads(self):
        skus = [sku("Standard_D4s_v5", "uksouth"), sku("Standard_B2s"), sku("Standard_D4s_v5")]
        with tempfile.TemporaryDirectory() as directory, patch.object(vm_size_report, "az", return_value=skus):
            path = Path(directory) / "catalogue.txt"
            self.assertEqual(refresh_catalogue(path), 2)
            date, names = read_catalogue(path)
        self.assertEqual(date, datetime.date.today().isoformat())
        self.assertEqual(list(names.values()), ["Standard_B2s", "Standard_D4s_v5"])

    def test_refresh_keeps_the_catalogue_if_azure_lists_nothing(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(vm_size_report, "az", return_value=[]):
            path = Path(directory) / "catalogue.txt"
            path.write_text("Standard_B2s\n")
            with self.assertRaises(ValueError):
                refresh_catalogue(path)
            self.assertEqual(path.read_text(), "Standard_B2s\n")


class ReportTests(unittest.TestCase):
    files = {
        "main.tf": 'a = "Standard_D4s_v5"\nb = "Standard_B2s"\nc = "Standard_DS2_v3"\nd = "Standard_D8s_v5"\n',
        "docs/sizes.md": "Use `Standard_B2s` or `Standard_E2s_v5`.\n",
        "api_http_requests/API User Journey.http": '"vm_size": "Standard_A1"\n',
        "catalogue.txt": "# Refreshed on 2026-10-23\nStandard_B2s\nStandard_D4s_v5\nStandard_D8s_v5\nStandard_E2s_v5\n",
    }

    def run_report(self, *args, skus=(), az_error=None):
        def fake_az(command, subscription=None):
            if az_error:
                raise az_error
            return {"name": "Test subscription", "id": "0000"} if command[0] == "account" else list(skus)

        with tempfile.TemporaryDirectory() as directory:
            repo = git_repo(directory, self.files)
            with (
                patch.object(vm_size_report, "az", side_effect=fake_az) as az,
                patch("sys.stdout", new_callable=io.StringIO) as output,
            ):
                vm_size_report.main([*args, "--repo", str(repo), "--catalogue", str(repo / "catalogue.txt")])
        return output.getvalue(), az

    def test_report_skips_the_files_of_this_tool(self):
        files = {**self.files, "own.md": "For example `Standard_F2s_v2`.\n"}
        with tempfile.TemporaryDirectory() as directory:
            repo = git_repo(directory, files)
            with (
                patch.object(vm_size_report, "OWN_FILES", {(repo / "own.md").resolve()}),
                patch("sys.stdout", new_callable=io.StringIO) as output,
            ):
                vm_size_report.main(["--repo", str(repo), "--catalogue", str(repo / "catalogue.txt")])
        report = output.getvalue()
        self.assertIn("`Standard_D4s_v5`", report)
        self.assertNotIn("Standard_F2s_v2", report)
        self.assertNotIn("own.md", report)

    def test_report_skips_the_tool_files_of_another_repository(self):
        files = {
            **self.files,
            "devops/scripts/vm_size_catalogue.txt": "# Refreshed on 2026-10-23\nStandard_F2s_v2\n",
            "docs/tre-admins/vm-size-availability.md": "For example `Standard_F4s_v2`.\n",
        }
        with tempfile.TemporaryDirectory() as directory:
            repo = git_repo(directory, files)
            with patch("sys.stdout", new_callable=io.StringIO) as output:
                vm_size_report.main(["--repo", str(repo), "--catalogue", str(repo / "catalogue.txt")])
        report = output.getvalue()
        self.assertIn("`Standard_D4s_v5`", report)
        self.assertNotIn("Standard_F2s_v2", report)
        self.assertNotIn("Standard_F4s_v2", report)

    def test_region_report_shows_problems_first_and_code_before_docs(self):
        skus = [
            sku("Standard_B2s", "switzerlandnorth", {"type": "Location"}),
            sku("Standard_D4s_v5", "switzerlandnorth"),
            sku("Standard_D4s_v5", "uksouth"),
            sku("Standard_B2s", "uksouth"),
            sku("Standard_E2s_v5", "uksouth"),
            sku("Standard_D8s_v5", "uksouth"),
        ]
        report, az = self.run_report("--region", "Switzerland North,uksouth", skus=skus)

        self.assertEqual(az.call_count, 2)
        self.assertEqual(
            [[row[0], row[1], row[4], row[5], row[6]] for row in table_rows(report)],
            [
                ["`Standard_DS2_v3`", "VM", "❓ unknown name", "❓ unknown name", "code 1"],
                ["`Standard_A1`", "VM", "❓ unknown name", "❓ unknown name", "sample 1"],
                ["`Standard_B2s`", "VM", "⛔ blocked", "✅ available", "code 1, docs 1"],
                ["`Standard_D8s_v5`", "VM", "❌ not offered", "✅ available", "code 1"],
                ["`Standard_E2s_v5`", "VM", "❌ not offered", "✅ available", "docs 1"],
                ["`Standard_D4s_v5`", "VM", "✅ available", "✅ available", "code 1"],
            ],
        )
        self.assertIn("| ⛔ Blocked | 1 | 0 |", report)
        self.assertIn("- Catalogue: 4 VM sizes, refreshed 2026-10-23", report)
        self.assertIn("- Subscription: Test subscription\n", report)
        self.assertNotIn("0000", report)

    def test_hide_subscription_leaves_the_subscription_out(self):
        report, az = self.run_report("--region", "switzerlandnorth", "--hide-subscription", skus=[sku("Standard_B2s")])
        self.assertEqual([call.args[0][0] for call in az.call_args_list], ["vm", "account"])
        self.assertNotIn("Subscription", report)

    def test_report_without_a_region_needs_no_azure_login(self):
        report, az = self.run_report()
        az.assert_not_called()
        self.assertEqual(
            [[row[0], row[2]] for row in table_rows(report)],
            [
                ["`Standard_DS2_v3`", "❓ unknown name"],
                ["`Standard_A1`", "❓ unknown name"],
                ["`Standard_B2s`", "✔️ in catalogue"],
                ["`Standard_D4s_v5`", "✔️ in catalogue"],
                ["`Standard_D8s_v5`", "✔️ in catalogue"],
                ["`Standard_E2s_v5`", "✔️ in catalogue"],
            ],
        )

    def test_link_base_makes_links_to_the_lines(self):
        report, _ = self.run_report("--link-base", "https://github.com/org/repo/blob/abc123/")
        self.assertIn(
            "- [`api_http_requests/API User Journey.http:1`]"
            "(https://github.com/org/repo/blob/abc123/api_http_requests/API%20User%20Journey.http#L1) (sample)",
            report,
        )

    def test_region_without_vm_sizes_stops_the_report(self):
        with self.assertRaises(SystemExit) as stop:
            self.run_report("--region", "switzerlandnorth,nowhere", skus=[sku("Standard_B2s")])
        self.assertEqual(str(stop.exception), "Azure lists no VM sizes in nowhere. Check the region names.")

    def test_azure_cli_error_shows_its_message(self):
        error = subprocess.CalledProcessError(1, ["az", "vm"], stderr="ERROR: Please run 'az login'.\n")
        with self.assertRaises(SystemExit) as stop:
            self.run_report("--region", "switzerlandnorth", az_error=error)
        self.assertEqual(str(stop.exception), "az failed: ERROR: Please run 'az login'.")

    def test_invalid_or_empty_region_stops_before_azure(self):
        for value in ("eastus;whoami", " , "):
            with (
                self.subTest(value=value),
                patch("sys.stderr", new_callable=io.StringIO),
                self.assertRaises(SystemExit) as stop,
            ):
                self.run_report("--region", value)
            self.assertEqual(stop.exception.code, 2)


if __name__ == "__main__":
    unittest.main()

"""Exercise the production review-VM bootstrap with mocked Windows/network commands."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    ROOT / "templates/workspace_services/guacamole/user_resources/guacamole-azure-windowsvm/terraform/vm/vm_config.ps1"
)
HARNESS = r"""
$ErrorActionPreference = "Stop"
$settings = $env:BOOTSTRAP_TEST_SETTINGS | ConvertFrom-Json
$source = Get-Content -Raw $env:BOOTSTRAP_SOURCE
$source = $source.Replace('${nexus_proxy_url}', 'https://nexus.example.test')
$parseErrors = $null
$tokens = $null
$ast = [System.Management.Automation.Language.Parser]::ParseInput($source, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors) { throw $parseErrors[0] }
$definition = $ast.Find({ param($node)
  $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Install-TreTool'
}, $true)
Invoke-Expression $definition.Extent.Text
function Wait-ForNexus { return $settings.nexus_ready }
function Configure-RProxy {}
function Configure-CondaProxy {}
function Start-Sleep {}
function Invoke-WebRequest {
  param($Uri, $Method, $OutFile, [switch]$UseBasicParsing, $TimeoutSec)
  if ($Method -eq 'Head' -and $settings.package_missing) { throw 'PACKAGE_MISSING' }
  if ($OutFile -and $settings.download_failed) { throw 'DOWNLOAD_FAILED' }
}
function Start-Process {
  param($FilePath, $ArgumentList, [switch]$Wait, [switch]$PassThru, [switch]$NoNewWindow)
  return [pscustomobject]@{ ExitCode = $settings.exit_code }
}
function Get-Command {
  param($Name, $ErrorAction)
  if (-not $settings.cli_missing) { return [pscustomobject]@{Name = 'az'} }
}
function az { $global:LASTEXITCODE = $settings.cli_exit_code }
$NexusActionsEnabled = $true
$RequireAzureCli = $settings.required
$InstallAzureCli = $true
$ConfigureConda = $false
$AzureCliVersion = '2.88.0'
$ToolsDir = 'test-tools'
$start = $source.IndexOf('# Make sure the proxy is up')
$end = $source.IndexOf('$VsCodeSetup =')
Invoke-Expression $source.Substring($start, $end - $start)
Write-Host 'BOOTSTRAP_OK'
"""


@unittest.skipUnless(shutil.which("pwsh"), "PowerShell is required to execute the Windows bootstrap regression tests")
class ReviewVmPrerequisiteTests(unittest.TestCase):
    def run_bootstrap(self, **overrides):
        settings = {
            "required": True,
            "nexus_ready": True,
            "package_missing": False,
            "download_failed": False,
            "exit_code": 0,
            "cli_missing": False,
            "cli_exit_code": 0,
            **overrides,
        }
        with tempfile.TemporaryDirectory() as folder:
            harness = Path(folder) / "bootstrap-test.ps1"
            harness.write_text(HARNESS)
            result = subprocess.run(
                ["pwsh", "-NoLogo", "-NoProfile", "-File", str(harness)],
                env={**os.environ, "BOOTSTRAP_SOURCE": str(SCRIPT), "BOOTSTRAP_TEST_SETTINGS": json.dumps(settings)},
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            return result

    def test_missing_nexus_or_package_fails_before_install(self):
        for changes, message in (
            ({"nexus_ready": False}, "reachable Nexus"),
            ({"package_missing": True}, "package is unavailable"),
        ):
            with self.subTest(changes=changes):
                result = self.run_bootstrap(**changes)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
                self.assertNotIn("Installing Azure CLI", result.stdout)

    def test_required_cli_download_installer_and_execution_failures_stop_bootstrap(self):
        for changes, message in (
            ({"download_failed": True}, "could not be installed"),
            ({"exit_code": 1603}, "could not be installed"),
            ({"cli_missing": True}, "executable was not found"),
            ({"cli_exit_code": 1}, "failed its version check"),
        ):
            with self.subTest(changes=changes):
                result = self.run_bootstrap(**changes)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
                self.assertNotIn("BOOTSTRAP_OK", result.stdout)

    def test_success_and_msi_reboot_required_code_are_accepted(self):
        for code in (0, 3010):
            with self.subTest(code=code):
                result = self.run_bootstrap(exit_code=code)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("BOOTSTRAP_OK", result.stdout)

    def test_optional_cli_preserves_best_effort_behaviour(self):
        for changes in ({"nexus_ready": False, "download_failed": True}, {"exit_code": 1603}):
            with self.subTest(changes=changes):
                result = self.run_bootstrap(required=False, **changes)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("WARNING:", result.stdout)
                self.assertIn("BOOTSTRAP_OK", result.stdout)

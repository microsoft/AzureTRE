"""Check the private storage, database and secret settings of the Gitea services."""

import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "templates/workspace_services/gitea/terraform"
START_SCRIPT = ROOT / "templates/workspace_services/gitea/docker/configure_gitea.sh"
ADMIN_SCRIPT = ROOT / "templates/workspace_services/gitea/docker/configure_gitea_admin.sh"
SHARED_DOCKERFILE = ROOT / "templates/shared_services/gitea/docker/Dockerfile"
SECRETS = ("GITEA_PASSWD", "GITEA_OPENID_CLIENT_SECRET")


def block(source, header):
    return source.split(header + " {", 1)[1].split("\n}", 1)[0]


class GiteaBundleContractTests(unittest.TestCase):
    def test_share_uses_resource_manager(self):
        # With storage_account_name, the provider uses the file endpoint. The TRE firewall blocks it
        # before the private endpoint exists and after Terraform deletes the private endpoint.
        share = block((BUNDLE / "storage.tf").read_text(), 'resource "azurerm_storage_share" "gitea"')
        self.assertRegex(share, r"\n  storage_account_id\s*=\s*azurerm_storage_account\.gitea\.id\n")
        self.assertNotIn("storage_account_name", share)

    def test_server_disables_public_network_access(self):
        server = block((BUNDLE / "mysql.tf").read_text(), 'resource "azurerm_mysql_flexible_server" "gitea"')
        self.assertRegex(server, r'\n  public_network_access\s*=\s*"Disabled"\n')

    def test_start_script_prints_no_secret(self):
        # The web app sends the console output to Log Analytics.
        for script in (START_SCRIPT, ADMIN_SCRIPT):
            for line in script.read_text().splitlines():
                if line.lstrip().startswith(("echo", "printf")) or "set -x" in line:
                    for secret in SECRETS:
                        with self.subTest(script=script.name, line=line, secret=secret):
                            self.assertNotIn(secret, line)

    def test_admin_script_hides_secrets_in_gitea_output(self):
        # Gitea prints its full command line when a command fails.
        secrets = {
            "GITEA_PASSWD": "pass$word[1]",
            "GITEA_OPENID_CLIENT_SECRET": "client*secret",
            "GITEA__database__PASSWD": "db.secret",
        }
        with tempfile.TemporaryDirectory() as folder:
            stub = Path(folder) / "gitea"
            stub.write_text('#!/bin/bash\necho "[F] Failed to run app with [gitea $*]"\nexit 1\n')
            stub.chmod(0o755)
            environment = {
                **secrets,
                "PATH": f"{folder}{os.pathsep}{os.environ['PATH']}",
                "GITEA_USERNAME": "giteaadmin",
                "GITEA_EMAIL": "giteaadmin@example.com",
                "GITEA_OPENID_CLIENT_ID": "client-id",
                "GITEA_OPENID_AUTHORITY": "https://login.example.com/tenant/v2.0",
            }
            result = subprocess.run(
                ["bash", str(ADMIN_SCRIPT)], env=environment, capture_output=True, text=True, check=False
            )
        output = result.stdout + result.stderr
        for name, value in secrets.items():
            with self.subTest(secret=name):
                self.assertNotIn(value, output)
        self.assertIn("user create --admin --username=giteaadmin --password=***", output)
        self.assertIn("add-oauth --name oidc --provider openidConnect --key client-id --secret ***", output)

    def test_admin_create_makes_no_access_token(self):
        # Gitea prints a new access token to the console output.
        for source in (START_SCRIPT, SHARED_DOCKERFILE):
            commands = [line for line in source.read_text().splitlines() if not line.lstrip().startswith("#")]
            with self.subTest(source=source.name):
                self.assertNotIn("--access-token", "\n".join(commands))

    def test_openid_secret_is_a_key_vault_reference(self):
        # A plain value is visible in the app settings and in the Terraform state.
        webapp = (BUNDLE / "gitea-webapp.tf").read_text()
        value = re.search(r"\n    GITEA_OPENID_CLIENT_SECRET\s*=\s*(.+)\n", webapp).group(1)
        self.assertRegex(value, r'^"@Microsoft\.KeyVault\(SecretUri=.+secrets/workspace-client-secret\)"$')
        self.assertNotIn('data "azurerm_key_vault_secret" "client_secret"', (BUNDLE / "data.tf").read_text())

    def test_identity_reads_only_its_key_vault_references(self):
        # The workspace Key Vault also has the secrets of the other workspace services.
        webapp = (BUNDLE / "gitea-webapp.tf").read_text()
        for name in re.findall(r'resource "azurerm_role_assignment" "(\w+)"', webapp):
            assignment = block(webapp, f'resource "azurerm_role_assignment" "{name}"')
            with self.subTest(role=name):
                self.assertNotRegex(assignment, r"\n  scope\s*=\s*data\.azurerm_key_vault\.ws\.id\n")
        roles = block(webapp, 'resource "azurerm_role_assignment" "keyvault_gitea_secret_role"')
        scopes = re.findall(r"\n    \w+\s*=\s*(.+)", roles.split("for_each = {", 1)[1].split("\n  }", 1)[0])
        references = re.findall(r"@Microsoft\.KeyVault\(SecretUri=(.+?)\)", webapp)
        self.assertEqual(len(scopes), len(references))
        self.assertIn('"${data.azurerm_key_vault.ws.id}/secrets/workspace-client-secret"', scopes)

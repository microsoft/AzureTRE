"""Record identities from actual prerequisite selection without resource writes."""

from contextlib import asynccontextmanager
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from e2e_tests import bundle_evidence
from e2e_tests.resources import strings

try:
    from e2e_tests.resources import nexus as prerequisites

    nexus_context = prerequisites.nexus_prerequisites
except ImportError:
    from e2e_tests import test_guacamole_linuxvm as prerequisites

    nexus_context = prerequisites.linux_vm_nexus


class ReusedPrerequisiteEvidenceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.report = bundle_evidence.BundleReport(Path(self.directory) / "report.json", {})
        bundle_evidence.activate(self.report)
        self.addCleanup(bundle_evidence.activate, None)
        self.enterContext(patch.object(prerequisites, "get_admin_token", AsyncMock(return_value="secret-token")))
        self.certs = {
            "id": "cert-id",
            "templateName": strings.CERTS_SHARED_SERVICE,
            "templateVersion": "1.2.3",
            "deploymentStatus": "deployed",
            "isEnabled": True,
            "properties": {"domain_prefix": "nexus", "cert_name": "cert-name", "secret": "never-copy"},
        }
        self.nexus = {
            "id": "nexus-id",
            "templateName": strings.NEXUS_SHARED_SERVICE,
            "templateVersion": "3.11.0",
            "deploymentStatus": "deployed",
            "isEnabled": True,
            "properties": {"ssl_cert_name": "cert-name", "secret": "never-copy"},
        }

    async def test_reused_nexus_and_matching_certificate_are_recorded_without_writes(self):
        unrelated = {**self.certs, "id": "unrelated", "properties": {"cert_name": "another-cert"}}
        with (
            patch.object(
                prerequisites,
                "get_resource",
                AsyncMock(return_value={"sharedServices": [self.nexus, self.certs, unrelated]}),
            ),
            patch.object(prerequisites, "temporary_resource", side_effect=AssertionError("Unexpected write")),
        ):
            async with nexus_context(True):
                pass
        self.assertEqual({r["id"] for r in self.report.data["reused_resources"]}, {"nexus-id", "cert-id"})
        self.assertEqual(self.report.data["reused_resources"][0]["templateVersion"], "3.11.0")
        self.assertEqual(self.report.data["resources"], [])
        self.assertNotIn("never-copy", self.report.filename.read_text())
        self.assertNotIn("secret-token", self.report.filename.read_text())

    async def test_existing_certificate_is_recorded_when_new_nexus_is_created(self):
        @asynccontextmanager
        async def create(*args, **kwargs):
            yield "/shared-services/new-nexus"

        with (
            patch.object(prerequisites, "get_resource", AsyncMock(return_value={"sharedServices": [self.certs]})),
            patch.object(prerequisites, "temporary_resource", create),
            patch.object(prerequisites.config, "TEST_ACCEPT_NEXUS_EULA", True),
        ):
            async with nexus_context(True):
                pass
        self.assertEqual([r["id"] for r in self.report.data["reused_resources"]], ["cert-id"])

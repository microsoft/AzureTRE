"""Test Nexus prerequisites, explicit consent and ownership of cleanup resources."""

import json
import unittest
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient, MockTransport, Response

from e2e_tests import helpers
from e2e_tests import test_guacamole_linuxvm as linuxvm
from e2e_tests.resources import resource, strings


class NexusPrerequisiteTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.services = []
        self.requests = []
        self.outcomes = {}
        self.enterContext(patch.object(helpers.config, "TRE_URL", "https://tre.example.test"))
        self.enterContext(patch.object(linuxvm, "get_admin_token", new=AsyncMock(return_value="admin-token")))
        self.enterContext(patch.object(linuxvm.config, "TEST_ACCEPT_NEXUS_EULA", True))
        self.enterContext(
            patch.object(
                resource, "AsyncClient", side_effect=lambda **_: AsyncClient(transport=MockTransport(self.handle))
            )
        )

    def handle(self, request):
        self.requests.append(request)
        if request.method == "GET" and request.url.path == strings.API_SHARED_SERVICES:
            return Response(200, json={"sharedServices": self.services})
        response_status = 200
        if request.method == "POST":
            payload = json.loads(request.content)
            kind = "nexus" if payload["templateName"] == strings.NEXUS_SHARED_SERVICE else "certs"
            if kind == "nexus":
                self.assertIs(payload["properties"]["accept_nexus_eula"], True)
            phase, response_status, state = "install", 202, "deploying"
        elif request.method == "GET":
            kind, phase = request.url.path.rsplit("/", 1)[-1].split("-")
            state = self.outcomes.get(
                (kind, phase), {"install": "deployed", "disable": "updated", "delete": "deleted"}[phase]
            )
        else:
            kind = request.url.path.rsplit("/", 1)[-1]
            if request.method == "PATCH":
                self.assertEqual(json.loads(request.content), {"isEnabled": False})
                phase, response_status, state = "disable", 202, "updating"
            else:
                self.assertEqual(request.method, "DELETE")
                phase, state = "delete", "deleting"
        return Response(
            response_status,
            headers={"Location": f"/api/operations/{kind}-{phase}"},
            json={
                "operation": {
                    "resourcePath": f"/shared-services/{kind}",
                    "resourceId": kind,
                    "status": state,
                    "message": "Mock operation",
                    "steps": [],
                }
            },
        )

    def nexus(self, **overrides):
        return {
            "templateName": strings.NEXUS_SHARED_SERVICE,
            "templateVersion": "3.11.0",
            "deploymentStatus": "deployed",
            "isEnabled": True,
            **overrides,
        }

    def certs(self, **overrides):
        return {
            "templateName": strings.CERTS_SHARED_SERVICE,
            "deploymentStatus": "deployed",
            "isEnabled": True,
            "properties": {"domain_prefix": "nexus", "cert_name": "existing-cert"},
            **overrides,
        }

    def deleted(self):
        return [request.url.path.rsplit("/", 1)[-1] for request in self.requests if request.method == "DELETE"]

    async def test_existing_nexus_is_reused_without_consent_or_mutation(self):
        self.services = [self.nexus()]
        with patch.object(linuxvm.config, "TEST_ACCEPT_NEXUS_EULA", False):
            async with linuxvm.linux_vm_nexus(True):
                pass
        self.assertEqual([request.method for request in self.requests], ["GET"])

    async def test_missing_nexus_requires_explicit_consent_before_creation(self):
        with patch.object(linuxvm.config, "TEST_ACCEPT_NEXUS_EULA", False):
            with self.assertRaisesRegex(AssertionError, "explicitly accept"):
                async with linuxvm.linux_vm_nexus(True):
                    self.fail("Prerequisites should not be ready")
        self.assertEqual([request.method for request in self.requests], ["GET"])

    async def test_ambiguous_existing_nexus_is_not_mutated(self):
        self.services = [self.nexus(), self.nexus()]
        with self.assertRaisesRegex(AssertionError, "at most one Nexus"):
            async with linuxvm.linux_vm_nexus(True):
                self.fail("Ambiguous ownership must stop setup")
        self.assertEqual([request.method for request in self.requests], ["GET"])

    async def test_old_or_failed_nexus_is_not_silently_reused_or_replaced(self):
        for changes in ({"templateVersion": "3.10.4"}, {"deploymentStatus": "deployment_failed"}, {"isEnabled": False}):
            with self.subTest(changes=changes):
                self.services = [self.nexus(**changes)]
                self.requests.clear()
                with self.assertRaises(AssertionError):
                    async with linuxvm.linux_vm_nexus(True):
                        self.fail("Unsuitable Nexus should be rejected")
                self.assertEqual([request.method for request in self.requests], ["GET"])

    async def test_created_resources_are_deleted_in_reverse_dependency_order(self):
        async with linuxvm.linux_vm_nexus(True):
            self.assertEqual(self.deleted(), [])
        posts = [json.loads(request.content)["templateName"] for request in self.requests if request.method == "POST"]
        self.assertEqual(posts, [strings.CERTS_SHARED_SERVICE, strings.NEXUS_SHARED_SERVICE])
        self.assertEqual(self.deleted(), ["nexus", "certs"])

    async def test_existing_certificate_service_is_preserved(self):
        self.services = [self.certs(properties={"domain_prefix": "other", "cert_name": "unrelated"}), self.certs()]
        async with linuxvm.linux_vm_nexus(True):
            pass
        posts = [json.loads(request.content) for request in self.requests if request.method == "POST"]
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["properties"]["ssl_cert_name"], "existing-cert")
        self.assertEqual(self.deleted(), ["nexus"])

    async def test_failed_existing_certificate_service_requires_repair(self):
        self.services = [self.certs(deploymentStatus="deployment_failed")]
        with self.assertRaisesRegex(AssertionError, "Repair the existing Nexus certificate service"):
            async with linuxvm.linux_vm_nexus(True):
                self.fail("A failed certificate service must not be reused")
        self.assertEqual([request.method for request in self.requests], ["GET"])

    async def test_failed_nexus_deployment_cleans_up_both_owned_resources(self):
        self.outcomes[("nexus", "install")] = "deployment_failed"
        self.outcomes[("nexus", "disable")] = "updating_failed"
        with self.assertRaises(AssertionError):
            async with linuxvm.linux_vm_nexus(True):
                self.fail("A failed Nexus install must not be used")
        self.assertEqual(self.deleted(), ["nexus", "certs"])

    async def test_failed_certificate_deployment_does_not_create_nexus(self):
        self.outcomes[("certs", "install")] = "deployment_failed"
        with self.assertRaises(AssertionError):
            async with linuxvm.linux_vm_nexus(True):
                self.fail("A failed certificate install must stop setup")
        posts = [json.loads(request.content)["templateName"] for request in self.requests if request.method == "POST"]
        self.assertEqual(posts, [strings.CERTS_SHARED_SERVICE])
        self.assertEqual(self.deleted(), ["certs"])

    async def test_vm_failure_preserved_while_shared_resources_are_cleaned(self):
        failure = RuntimeError("VM bootstrap failed")
        bootstrap_vm = AsyncMock(side_effect=failure)
        with self.assertRaisesRegex(RuntimeError, "VM bootstrap failed") as caught:
            async with linuxvm.linux_vm_nexus(True):
                await bootstrap_vm()
        self.assertIs(caught.exception, failure)
        self.assertEqual(self.deleted(), ["nexus", "certs"])


if __name__ == "__main__":
    unittest.main()

"""Test Nexus prerequisites, explicit consent and ownership of cleanup resources."""

import asyncio
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient, MockTransport, Response
from jsonschema import ValidationError, validate

from api_app.services.schema_service import enrich_shared_service_template
from e2e_tests import helpers, conftest as fixtures
from e2e_tests.resources import nexus
from e2e_tests.resources import resource, strings


class NexusPrerequisiteTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.services = []
        self.requests = []
        self.outcomes = {}
        templates = Path(__file__).resolve().parents[2] / "templates/shared_services"
        self.schemas = {
            strings.NEXUS_SHARED_SERVICE: json.loads(
                (templates / "sonatype-nexus-vm/template_schema.json").read_text()
            ),
            strings.CERTS_SHARED_SERVICE: json.loads((templates / "certs/template_schema.json").read_text()),
        }
        self.schemas = {
            name: enrich_shared_service_template(SimpleNamespace(model_dump=lambda schema=schema, **_: schema))
            for name, schema in self.schemas.items()
        }
        self.enterContext(patch.object(helpers.config, "TRE_URL", "https://tre.example.test"))
        self.enterContext(patch.object(nexus, "get_admin_token", new=AsyncMock(return_value="admin-token")))
        self.enterContext(patch.object(nexus.config, "TEST_ACCEPT_NEXUS_EULA", True))
        self.enterContext(
            patch.object(
                resource, "AsyncClient", side_effect=lambda **_: AsyncClient(transport=MockTransport(self.handle))
            )
        )

    def handle(self, request):
        self.requests.append(request)
        if request.method == "GET" and request.url.path == strings.API_SHARED_SERVICES:
            return Response(200, json={"sharedServices": self.services})
        if request.method == "GET" and request.url.path in ("/api/shared-services/nexus", "/api/shared-services/certs"):
            return Response(200, json={"sharedService": {"isEnabled": False}})
        response_status = 200
        if request.method == "POST":
            payload = json.loads(request.content)
            validate(payload["properties"], self.schemas[payload["templateName"]])
            kind = "nexus" if payload["templateName"] == strings.NEXUS_SHARED_SERVICE else "certs"
            if kind == "nexus":
                self.assertIs(payload["properties"]["accept_nexus_eula"], True)
                self.assertEqual(payload["properties"]["vm_size"], "Standard_D2s_v3")
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
        with patch.object(nexus.config, "TEST_ACCEPT_NEXUS_EULA", False):
            async with nexus.nexus_prerequisites(True):
                pass
        self.assertEqual([request.method for request in self.requests], ["GET"])

    async def test_missing_nexus_requires_explicit_consent_before_creation(self):
        with patch.object(nexus.config, "TEST_ACCEPT_NEXUS_EULA", False):
            with self.assertRaisesRegex(AssertionError, "explicitly accept"):
                async with nexus.nexus_prerequisites(True):
                    self.fail("Prerequisites should not be ready")
        self.assertEqual([request.method for request in self.requests], ["GET"])

    async def test_ambiguous_existing_nexus_is_not_mutated(self):
        self.services = [self.nexus(), self.nexus()]
        with self.assertRaisesRegex(AssertionError, "at most one Nexus"):
            async with nexus.nexus_prerequisites(True):
                self.fail("Ambiguous ownership must stop setup")
        self.assertEqual([request.method for request in self.requests], ["GET"])

    async def test_old_or_failed_nexus_is_not_silently_reused_or_replaced(self):
        for changes in ({"templateVersion": "3.10.4"}, {"deploymentStatus": "deployment_failed"}, {"isEnabled": False}):
            with self.subTest(changes=changes):
                self.services = [self.nexus(**changes)]
                self.requests.clear()
                with self.assertRaises(AssertionError):
                    async with nexus.nexus_prerequisites(True):
                        self.fail("Unsuitable Nexus should be rejected")
                self.assertEqual([request.method for request in self.requests], ["GET"])

    async def test_created_resources_are_deleted_in_reverse_dependency_order(self):
        async with nexus.nexus_prerequisites(True):
            self.assertEqual(self.deleted(), [])
        posts = [json.loads(request.content)["templateName"] for request in self.requests if request.method == "POST"]
        self.assertEqual(posts, [strings.CERTS_SHARED_SERVICE, strings.NEXUS_SHARED_SERVICE])
        self.assertEqual(self.deleted(), ["nexus", "certs"])

    async def test_existing_certificate_service_is_preserved(self):
        self.services = [self.certs()]
        async with nexus.nexus_prerequisites(True):
            pass
        posts = [json.loads(request.content) for request in self.requests if request.method == "POST"]
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["properties"]["ssl_cert_name"], "existing-cert")
        self.assertEqual(self.deleted(), ["nexus"])

    async def test_both_prerequisites_include_inherited_required_properties(self):
        async with nexus.nexus_prerequisites(True):
            pass
        posts = [json.loads(request.content) for request in self.requests if request.method == "POST"]
        self.assertEqual(len(posts), 2)
        for payload in posts:
            with self.subTest(template=payload["templateName"]):
                schema = self.schemas[payload["templateName"]]
                validate(payload["properties"], schema)
                del payload["properties"]["description"]
                with self.assertRaisesRegex(ValidationError, "'description' is a required property"):
                    validate(payload["properties"], schema)

    async def test_unrelated_certificate_service_is_not_replaced(self):
        # The API allows only one active service per template.
        self.services = [self.certs(properties={"domain_prefix": "other", "cert_name": "unrelated"})]
        with self.assertRaisesRegex(AssertionError, "belongs to another domain"):
            async with nexus.nexus_prerequisites(True):
                self.fail("An unrelated certificate service must be preserved")
        self.assertEqual([request.method for request in self.requests], ["GET"])

    async def test_failed_existing_certificate_service_requires_repair(self):
        self.services = [self.certs(deploymentStatus="deployment_failed")]
        with self.assertRaisesRegex(AssertionError, "Repair the existing Nexus certificate service"):
            async with nexus.nexus_prerequisites(True):
                self.fail("A failed certificate service must not be reused")
        self.assertEqual([request.method for request in self.requests], ["GET"])

    async def test_failed_nexus_deployment_cleans_up_both_owned_resources(self):
        self.outcomes[("nexus", "install")] = "deployment_failed"
        self.outcomes[("nexus", "disable")] = "updating_failed"
        with self.assertRaises(AssertionError):
            async with nexus.nexus_prerequisites(True):
                self.fail("A failed Nexus install must not be used")
        self.assertEqual(self.deleted(), ["nexus", "certs"])

    async def test_failed_certificate_deployment_does_not_create_nexus(self):
        self.outcomes[("certs", "install")] = "deployment_failed"
        with self.assertRaises(AssertionError):
            async with nexus.nexus_prerequisites(True):
                self.fail("A failed certificate install must stop setup")
        posts = [json.loads(request.content)["templateName"] for request in self.requests if request.method == "POST"]
        self.assertEqual(posts, [strings.CERTS_SHARED_SERVICE])
        self.assertEqual(self.deleted(), ["certs"])

    async def test_vm_failure_preserved_while_shared_resources_are_cleaned(self):
        failure = RuntimeError("VM bootstrap failed")
        bootstrap_vm = AsyncMock(side_effect=failure)
        with self.assertRaisesRegex(RuntimeError, "VM bootstrap failed") as caught:
            async with nexus.nexus_prerequisites(True):
                await bootstrap_vm()
        self.assertIs(caught.exception, failure)
        self.assertEqual(self.deleted(), ["nexus", "certs"])

    async def test_prompt_nexus_delete_failure_retains_its_certificate(self):
        owned = nexus.nexus_prerequisites(True)
        await owned.__aenter__()
        self.services = [self.nexus(deploymentStatus="deleting_failed")]
        self.outcomes[("nexus", "delete")] = "deleting_failed"
        with self.assertRaises(AssertionError) as caught:
            await owned.__aexit__(None, None, None)
        self.assertEqual(self.deleted(), ["nexus"])
        self.assertIn("Retaining certificate dependency", str(caught.exception.__notes__))

    async def test_certificate_lookup_failure_retains_the_dependency(self):
        owned = nexus.nexus_prerequisites(True)
        await owned.__aenter__()
        with patch.object(nexus, "get_resource", AsyncMock(side_effect=RuntimeError("lookup failed"))):
            with self.assertRaisesRegex(RuntimeError, "lookup failed"):
                await owned.__aexit__(None, None, None)
        self.assertEqual(self.deleted(), ["nexus"])

    async def test_nested_cleanup_stops_at_one_deadline_and_retains_certificate(self):
        owned = nexus.nexus_prerequisites(True)
        await owned.__aenter__()
        self.outcomes[("nexus", "disable")] = "updating"
        with patch.object(fixtures, "CLEANUP_TIMEOUT_SECONDS", 0.01):
            with self.assertRaises(TimeoutError):
                async with fixtures.resource_cleanup_timeout("Nexus prerequisites"):
                    await asyncio.wait_for(owned.__aexit__(None, None, None), 0.5)
        mutations = [(request.method, request.url.path) for request in self.requests if request.method != "GET"]
        self.assertEqual(mutations[-1], ("PATCH", "/api/shared-services/nexus"))
        self.assertNotIn(("PATCH", "/api/shared-services/certs"), mutations)
        count = len(self.requests)
        await asyncio.sleep(0.01)
        self.assertEqual(len(self.requests), count)


if __name__ == "__main__":
    unittest.main()

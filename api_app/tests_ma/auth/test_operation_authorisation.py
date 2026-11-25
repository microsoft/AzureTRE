"""Exercise operation ownership through real routes, JWT validation and repository queries.

Only signing-key retrieval and Cosmos storage are replaced with synthetic fixtures.
The container adapter supports the simple predicates used by these routes.
"""

import copy
import json
import re
import socket
import time
from types import SimpleNamespace
from uuid import UUID

import httpx
import jwt
import pytest
import pytest_asyncio
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI

from api.dependencies.database import Database
from api.routes.shared_services import shared_services_router
from api.routes.workspaces import (
    workspaces_shared_router,
    workspace_services_workspace_router,
    user_resources_workspace_router,
)
from auth import registry
from core import config
from models.domain.operation import Operation, OperationStep
from models.domain.shared_service import SharedService
from models.domain.user_resource import UserResource
from models.domain.workspace import Workspace
from models.domain.workspace_service import WorkspaceService
from resources import strings


def uid(number):
    return str(UUID(int=number, version=4))


WA, WB, SA, SB, RA, RB, OTHER_RA, SHARED, OTHER_SHARED = [uid(n) for n in range(1, 10)]
CALLER = "synthetic-user-a"
PATH_A = f"/workspaces/{WA}"
PATH_B = f"/workspaces/{WB}"
PATH_SA = f"{PATH_A}/workspace-services/{SA}"
PATH_SB = f"{PATH_B}/workspace-services/{SB}"
PATH_RA = f"{PATH_SA}/user-resources/{RA}"
PATH_RB = f"{PATH_SB}/user-resources/{RB}"
PATH_OTHER_RA = f"{PATH_SA}/user-resources/{OTHER_RA}"
PATH_SHARED = f"/shared-services/{SHARED}"
ISSUER = "https://synthetic.invalid/tenant/v2.0"


class SyntheticContainer:
    def __init__(self, documents):
        self.documents = documents
        self.queries = []

    def query_items(self, *, query, parameters=None):
        self.queries.append({"query": query, "parameters": parameters})
        prefix = "SELECT * FROM c WHERE "
        assert query.startswith(prefix), query
        bindings = {p["name"]: p["value"] for p in parameters or []}
        predicates = []
        for clause in query[len(prefix) :].split(" AND "):
            match = re.fullmatch(r'c\.(\w+)\s*(!=|=)\s*("[^"]*"|@\w+)', clause)
            assert match, f"Unsupported synthetic query: {query}"
            field, operator, value = match.groups()
            value = bindings[value] if value.startswith("@") else json.loads(value)
            predicates.append((field, operator, value))

        async def rows():
            for document in self.documents:
                if all(
                    field in document and (document[field] == value if operator == "=" else document[field] != value)
                    for field, operator, value in predicates
                ):
                    yield copy.deepcopy(document)

        return rows()


def make_operation(number, resource_id, resource_path, resource_type):
    return Operation(
        id=uid(number),
        resourceId=resource_id,
        resourcePath=resource_path,
        action="upgrade",
        status="updating",
        message="Synthetic private operation details",
        user={"id": "synthetic-user-b", "name": "Synthetic User B", "roles": ["WorkspaceOwner"]},
        steps=[
            OperationStep(
                id=uid(number + 100),
                templateStepId="main",
                resourceId=resource_id,
                resourceTemplateName="synthetic-template",
                resourceType=resource_type,
                resourceAction="upgrade",
                status="updating",
            )
        ],
    ).model_dump(mode="json")


@pytest_asyncio.fixture
async def system(monkeypatch):
    # Block outbound network connections, including accidental Azure calls.
    original_connect = socket.socket.connect

    def no_network(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            raise AssertionError("Network access is prohibited in this local verification")
        return original_connect(sock, address)

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(config, "AAD_AUTHORITY_URL", "https://synthetic.invalid")
    monkeypatch.setattr(config, "AAD_TENANT_ID", "tenant")
    monkeypatch.setattr(config, "API_AUDIENCE", "synthetic-core")
    registry.get_core_validator.cache_clear()
    registry.get_workspace_validator.cache_clear()
    registry._shared_jwks_client.cache_clear()
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk.update(kid="synthetic-test-key", use="sig", alg="RS256")
    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", lambda self: {"keys": [public_jwk]})

    common = dict(
        templateName="synthetic-template", templateVersion="1.0.0", etag="synthetic-etag", deploymentStatus="deployed"
    )
    resources = [
        SharedService(id=SHARED, resourcePath=PATH_SHARED, **common),
        SharedService(id=OTHER_SHARED, resourcePath=f"/shared-services/{OTHER_SHARED}", **common),
        Workspace(id=WA, resourcePath=PATH_A, properties={"client_id": "synthetic-app-a"}, **common),
        Workspace(id=WB, resourcePath=PATH_B, properties={"client_id": "synthetic-app-b"}, **common),
        WorkspaceService(id=SA, workspaceId=WA, resourcePath=PATH_SA, **common),
        WorkspaceService(id=SB, workspaceId=WB, resourcePath=PATH_SB, **common),
        UserResource(
            id=RA, workspaceId=WA, parentWorkspaceServiceId=SA, ownerId=CALLER, resourcePath=PATH_RA, **common
        ),
        UserResource(
            id=RB,
            workspaceId=WB,
            parentWorkspaceServiceId=SB,
            ownerId="synthetic-user-b",
            resourcePath=PATH_RB,
            **common,
        ),
        UserResource(
            id=OTHER_RA,
            workspaceId=WA,
            parentWorkspaceServiceId=SA,
            ownerId="synthetic-other-user-a",
            resourcePath=PATH_OTHER_RA,
            **common,
        ),
    ]
    documents = {
        "other_shared_service": make_operation(35, OTHER_SHARED, f"/shared-services/{OTHER_SHARED}", "shared-service"),
        "workspace_a": make_operation(20, WA, PATH_A, "workspace"),
        "service_a": make_operation(21, SA, PATH_SA, "workspace-service"),
        "resource_a": make_operation(22, RA, PATH_RA, "user-resource"),
        "workspace_b": make_operation(30, WB, PATH_B, "workspace"),
        "service_b": make_operation(31, SB, PATH_SB, "workspace-service"),
        "resource_b": make_operation(32, RB, PATH_RB, "user-resource"),
        "other_resource_a": make_operation(33, OTHER_RA, PATH_OTHER_RA, "user-resource"),
        "shared_service": make_operation(34, SHARED, f"/shared-services/{SHARED}", "shared-service"),
    }
    resource_container = SyntheticContainer([r.model_dump(mode="json") for r in resources])
    operations_container = SyntheticContainer(list(documents.values()))

    async def get_container(container_name):
        return {"Resources": resource_container, "Operations": operations_container}[container_name]

    monkeypatch.setattr(Database, "get_container_proxy", staticmethod(get_container))
    app = FastAPI()
    for router in (
        workspaces_shared_router,
        workspace_services_workspace_router,
        user_resources_workspace_router,
        shared_services_router,
    ):
        app.include_router(router, prefix="/api")
    assert not app.dependency_overrides

    def token(role, audience=None, key=None):
        audience = audience or ("synthetic-core" if role in ("TREAdmin", "TREUser") else "synthetic-app-a")
        return jwt.encode(
            {
                "oid": CALLER,
                "name": "Synthetic User A",
                "roles": [role],
                "aud": audience,
                "iss": ISSUER,
                "exp": int(time.time()) + 300,
            },
            key or private_key,
            algorithm="RS256",
            headers={"kid": "synthetic-test-key"},
        )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://synthetic") as client:
        yield SimpleNamespace(client=client, token=token, docs=documents, operations=operations_container)
    registry.get_core_validator.cache_clear()
    registry.get_workspace_validator.cache_clear()
    registry._shared_jwks_client.cache_clear()


ACCESS_PATHS = [
    (PATH_A, "WorkspaceOwner", "workspace_a"),
    (PATH_A, "TREAdmin", "workspace_a"),
    (PATH_SA, "WorkspaceOwner", "service_a"),
    (PATH_SA, "AirlockManager", "service_a"),
    (PATH_RA, "WorkspaceOwner", "resource_a"),
    (PATH_RA, "WorkspaceResearcher", "resource_a"),
    (PATH_RA, "AirlockManager", "resource_a"),
    (PATH_SHARED, "TREAdmin", "shared_service"),
]
TARGETS = [
    "workspace_a",
    "service_a",
    "resource_a",
    "workspace_b",
    "service_b",
    "resource_b",
    "other_resource_a",
    "shared_service",
    "other_shared_service",
]
MISMATCHES = [
    (resource_path, role, target)
    for resource_path, role, own_target in ACCESS_PATHS
    for target in TARGETS
    if target != own_target
]


@pytest.mark.asyncio
@pytest.mark.parametrize("resource_path,role,target", MISMATCHES)
async def test_operation_for_another_resource_returns_not_found(system, resource_path, role, target):
    foreign = system.docs[target]
    response = await system.client.get(
        f"/api{resource_path}/operations/{foreign['id']}",
        headers={"Authorization": f"Bearer {system.token(role)}"},
    )
    assert response.status_code == 404, response.text
    assert response.json() == {"detail": strings.OPERATION_DOES_NOT_EXIST}


@pytest.mark.asyncio
@pytest.mark.parametrize("resource_path,role,target", ACCESS_PATHS)
async def test_own_operation_is_accessible(system, resource_path, role, target):
    operation = system.docs[target]
    response = await system.client.get(
        f"/api{resource_path}/operations/{operation['id']}",
        headers={"Authorization": f"Bearer {system.token(role)}"},
    )
    assert response.status_code == 200
    assert response.json()["operation"] == operation


@pytest.mark.asyncio
@pytest.mark.parametrize("resource_path,role,target", ACCESS_PATHS)
async def test_operation_list_remains_resource_scoped(system, resource_path, role, target):
    response = await system.client.get(
        f"/api{resource_path}/operations",
        headers={"Authorization": f"Bearer {system.token(role)}"},
    )
    assert response.status_code == 200
    assert response.json()["operations"] == [system.docs[target]]


@pytest.mark.asyncio
async def test_other_user_resource_ownership_is_still_required(system):
    operation = system.docs["other_resource_a"]
    headers = {"Authorization": f"Bearer {system.token('WorkspaceResearcher')}"}
    response = await system.client.get(f"/api{PATH_OTHER_RA}/operations/{operation['id']}", headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "resource_path,role,token_audience,expected",
    [
        (PATH_B, "WorkspaceOwner", "synthetic-app-a", 401),
        (PATH_SB, "WorkspaceOwner", "synthetic-app-a", 401),
        (PATH_RB, "WorkspaceResearcher", "synthetic-app-a", 401),
        (PATH_A, "WorkspaceResearcher", "synthetic-app-a", 403),
        (PATH_SA, "WorkspaceResearcher", "synthetic-app-a", 403),
        (PATH_RA, "UnassignedRole", "synthetic-app-a", 403),
        (PATH_RA, "WorkspaceResearcher", "synthetic-app-b", 401),
        (PATH_SHARED, "TREUser", "synthetic-core", 403),
        (PATH_SHARED, "WorkspaceOwner", "synthetic-app-a", 401),
    ],
)
async def test_role_and_audience_checks_remain_active(system, resource_path, role, token_audience, expected):
    operation = system.docs["resource_b"]
    response = await system.client.get(
        f"/api{resource_path}/operations/{operation['id']}",
        headers={"Authorization": f"Bearer {system.token(role, token_audience)}"},
    )
    assert response.status_code == expected, response.text
    assert not system.operations.queries


@pytest.mark.asyncio
@pytest.mark.parametrize("resource_path,role,target", ACCESS_PATHS)
@pytest.mark.parametrize(
    "case,expected", [("missing_token", 401), ("bad_signature", 401), ("missing_operation", 404), ("invalid_uuid", 422)]
)
async def test_invalid_operation_requests_are_rejected(system, resource_path, role, target, case, expected):
    operation_id = system.docs[target]["id"]
    signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048) if case == "bad_signature" else None
    headers = {"Authorization": f"Bearer {system.token(role, key=signing_key)}"}
    if case == "missing_token":
        headers = {}
    elif case == "missing_operation":
        operation_id = uid(999)
    elif case == "invalid_uuid":
        operation_id = "not-a-uuid"
    response = await system.client.get(f"/api{resource_path}/operations/{operation_id}", headers=headers)
    assert response.status_code == expected, response.text

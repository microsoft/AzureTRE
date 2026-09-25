"""Opt-in MCP checks using existing Foundry accounts and public documentation."""

import json
from pathlib import Path

import pytest

from e2e_tests.resources import foundry_mcp


pytestmark = [pytest.mark.foundry, pytest.mark.foundry_egress, pytest.mark.timeout(900)]


@pytest.fixture(scope="module")
def foundry_mcp_results(pytestconfig):
    path = pytestconfig.getoption("--foundry-mcp-config")
    if not path:
        pytest.skip("Live MCP checks require --foundry-mcp-config with three existing accounts")
    if hasattr(pytestconfig, "workerinput"):
        pytest.fail("Run the MCP checks with -n 0 so all nine cases share one set of probes")
    return foundry_mcp.run_probes(json.loads(Path(path).read_text()))


@pytest.fixture
def foundry_mcp_result(request, foundry_mcp_results):
    result = foundry_mcp_results[request.param]
    if result["state"] == "blocked":
        pytest.fail(f'Inconclusive {request.param}: {result["reason"]}; HTTP {result["http_status"]}')
    return result


@pytest.mark.parametrize("foundry_mcp_result", foundry_mcp.CASES, indirect=True, ids=foundry_mcp.CASES)
def test_foundry_mcp_access(foundry_mcp_result):
    assert foundry_mcp_result["state"] == "pass", (
        f'{foundry_mcp_result["reason"]}; HTTP {foundry_mcp_result["http_status"]}')

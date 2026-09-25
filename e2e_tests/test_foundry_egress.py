"""Opt-in model calls against existing Foundry accounts. No TRE deployment."""

import json
from pathlib import Path

import pytest

from e2e_tests.resources import foundry


pytestmark = [pytest.mark.foundry, pytest.mark.foundry_egress, pytest.mark.timeout(900)]


@pytest.fixture(scope="module")
def foundry_egress_results(pytestconfig):
    path = pytestconfig.getoption("--foundry-egress-config")
    if not path:
        pytest.skip("Live outbound checks require --foundry-egress-config with three existing accounts")
    if hasattr(pytestconfig, "workerinput"):
        pytest.fail("Run the outbound checks with -n 0 so all six cases share one set of probes")
    config = json.loads(Path(path).read_text())
    return foundry.run_probes(config)


@pytest.fixture
def foundry_image_result(request, foundry_egress_results):
    result = foundry_egress_results[request.param]
    if result["state"] == "blocked":
        # A fixture error is inconclusive, not a passed rejection or an expected failure.
        pytest.fail(f'Inconclusive {request.param}: {result["reason"]}; HTTP {result["http_status"]}')
    return result


@pytest.mark.parametrize("foundry_image_result", foundry.CASES, indirect=True, ids=foundry.CASES)
def test_foundry_image_url(foundry_image_result):
    assert foundry_image_result["state"] == "pass", (
        f'{foundry_image_result["reason"]}; HTTP {foundry_image_result["http_status"]}')

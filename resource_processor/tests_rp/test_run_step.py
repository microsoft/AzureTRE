import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from helpers import statuses
from vmss_porter import runner

MESSAGE = {
    "id": "resource-1",
    "action": "install",
    "stepId": "step-1",
    "operationId": "operation-1",
    "name": "bundle",
    "version": "1.0.0",
    "parameters": {},
}
CONFIG = {"deployment_status_queue": "status"}


def service_bus():
    sender = MagicMock(send_messages=AsyncMock())
    return MagicMock(get_queue_sender=MagicMock(return_value=sender)), sender


def body_of(message):
    return json.loads(str(message))


def bodies(sender):
    return [body_of(call.args[0]) for call in sender.send_messages.await_args_list]


@pytest.mark.asyncio
async def test_a_finished_step_sends_its_recorded_status_without_porter():
    record = {
        "operationId": "operation-1",
        "stepId": "step-1",
        "executionId": "first-run",
        "state": "finished",
        "status": statuses.pass_status_string_for["install"],
        "message": "install action completed successfully.",
        "outputs": True,
    }
    execution = MagicMock(read=AsyncMock(return_value=record), write=AsyncMock())
    client, sender = service_bus()
    outputs = [{"name": "url", "value": "https://example"}]
    with (
        patch.object(runner, "invoke_porter_action", AsyncMock()) as invoke,
        patch.object(runner, "get_porter_outputs", AsyncMock(return_value=(True, outputs))),
    ):
        assert await runner.run_step(MESSAGE, execution, client, CONFIG) is True
    invoke.assert_not_awaited()
    execution.write.assert_not_awaited()
    [body] = bodies(sender)
    assert body["executionId"] == "first-run"
    assert body["status"] == statuses.pass_status_string_for["install"]
    assert body["outputs"] == outputs


@pytest.mark.asyncio
async def test_a_recorded_failure_is_sent_again_without_outputs():
    record = {
        "operationId": "operation-1",
        "stepId": "step-1",
        "executionId": "first-run",
        "state": "finished",
        "status": statuses.failed_status_string_for["install"],
        "message": "Error message: failed",
        "outputs": False,
    }
    execution = MagicMock(read=AsyncMock(return_value=record), write=AsyncMock())
    client, sender = service_bus()
    with patch.object(runner, "get_porter_outputs", AsyncMock()) as outputs:
        assert await runner.run_step(MESSAGE, execution, client, CONFIG) is False
    outputs.assert_not_awaited()
    [body] = bodies(sender)
    assert body["status"] == statuses.failed_status_string_for["install"]
    assert "outputs" not in body


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "record",
    [
        {},
        {"operationId": "operation-1", "stepId": "step-1", "state": "running", "executionId": "crashed-run"},
        {"operationId": "operation-1", "stepId": "step-0", "state": "finished", "executionId": "earlier-step"},
        {"operationId": "operation-0", "stepId": "step-1", "state": "finished", "executionId": "other-operation"},
    ],
)
async def test_porter_runs_when_the_record_has_no_result_for_this_step(record):
    execution = MagicMock(read=AsyncMock(return_value=record), write=AsyncMock())
    with patch.object(runner, "invoke_porter_action", AsyncMock(return_value=True)) as invoke:
        assert await runner.run_step(MESSAGE, execution, MagicMock(), CONFIG) is True
    execution_id = invoke.await_args.kwargs["execution_id"]
    assert execution_id not in (record.get("executionId"), None)
    running = execution.write.await_args.args[0]
    assert running == {
        "operationId": "operation-1",
        "stepId": "step-1",
        "action": "install",
        "executionId": execution_id,
        "state": "running",
    }
    await invoke.await_args.kwargs["finish"]("deployed", "done", True)
    assert execution.write.await_args.args[0] == {
        **running,
        "state": "finished",
        "status": "deployed",
        "message": "done",
        "outputs": True,
    }


@pytest.mark.asyncio
async def test_each_status_has_the_execution_id_and_the_result_is_saved_before_the_final_status():
    client, sender = service_bus()
    events = []
    sender.send_messages.side_effect = lambda message: events.append(("send", body_of(message)["status"]))

    async def finish(status, message, with_outputs):
        events.append(("finish", status, with_outputs))

    with (
        patch.object(
            runner, "build_porter_command", AsyncMock(return_value=([["porter", "install"]], None, "p", None))
        ),
        patch.object(runner, "run_porter", AsyncMock(return_value=(0, "", ""))),
        patch.object(runner, "get_porter_outputs", AsyncMock(return_value=(True, []))),
    ):
        assert await runner.invoke_porter_action(MESSAGE, client, CONFIG, execution_id="run-2", finish=finish)
    assert events == [
        ("send", statuses.in_progress_status_string_for["install"]),
        ("finish", statuses.pass_status_string_for["install"], True),
        ("send", statuses.pass_status_string_for["install"]),
    ]
    assert {body["executionId"] for body in bodies(sender)} == {"run-2"}


@pytest.mark.asyncio
async def test_a_status_without_an_execution_has_no_execution_id():
    client, sender = service_bus()
    with (
        patch.object(
            runner, "build_porter_command", AsyncMock(return_value=([["porter", "install"]], None, "p", None))
        ),
        patch.object(runner, "run_porter", AsyncMock(return_value=(1, "", "failed"))),
    ):
        assert await runner.invoke_porter_action(MESSAGE, client, CONFIG) is False
    assert all("executionId" not in body for body in bodies(sender))


@pytest.mark.asyncio
@pytest.mark.parametrize("action, required", [("upgrade", "resource-1"), ("install", None), ("uninstall", None)])
async def test_only_an_upgrade_requires_the_installation(action, required):
    client, _ = service_bus()
    with (
        patch.object(runner, "build_porter_command", AsyncMock(return_value=([["porter", action]], None, "p", None))),
        patch.object(runner, "run_porter", AsyncMock(return_value=(1, "", "failed"))) as run_porter,
        patch.object(runner, "_confirm_porter_installation_removed", AsyncMock(return_value=False)),
    ):
        await runner.invoke_porter_action({**MESSAGE, "action": action}, client, CONFIG)
    assert run_porter.await_args.kwargs["required_installation"] == required


@pytest.mark.asyncio
@pytest.mark.parametrize("absent, porter_runs", [(True, False), (False, True)])
async def test_an_upgrade_does_not_install_a_deleted_resource(absent, porter_runs):
    commands = []

    async def helper(command, config, *args, **kwargs):
        commands.append(command)
        return 0, "", ""

    with (
        patch.object(runner, "run_command_helper", side_effect=helper),
        patch.object(runner, "azure_login_command", return_value=[]),
        patch.object(runner, "azure_acr_login_command", return_value=[]),
        patch.object(runner, "apply_porter_credentials_sets_command", return_value=[]),
        patch.object(runner, "_confirm_porter_installation_removed", AsyncMock(return_value=absent)),
    ):
        code, _, error = await runner.run_porter(
            [["porter", "installations", "apply"]], {}, required_installation="resource-1"
        )
    assert (["porter", "installations", "apply"] in commands) is porter_runs
    if absent:
        assert code == 1
        assert "An upgrade does not install a deleted resource" in error
    else:
        assert code == 0


def installation(installed=None, uninstalled=None, name="resource-1"):
    return {"name": name, "status": {"installed": installed, "uninstalled": uninstalled}}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "output, removed",
    [
        # An install can fail before Porter writes a record. An upgrade can repair it.
        ([], False),
        # Porter keeps the record after an uninstall, and `installations apply` then runs the install action.
        ([installation("2026-10-29T10:00:00.123456789Z", "2026-10-29T11:00:00.5Z")], True),
        ([installation(None, "2026-10-29T11:00:00Z")], True),
        ([installation("2026-10-29T12:00:00Z", "2026-10-29T11:00:00Z")], False),
        ([installation("2026-10-29T10:00:00Z")], False),
        # A failed install has neither time. An upgrade can repair it.
        ([installation()], False),
        ([installation(name="other-resource")], False),
        (None, False),
    ],
)
async def test_an_upgrade_finds_a_removed_installation(output, removed):
    result = (0, json.dumps(output), "") if output is not None else (1, "", "store not available")
    with patch.object(runner, "run_command_helper", AsyncMock(return_value=result)):
        assert await runner._confirm_porter_installation_removed("resource-1", {}) is removed


@pytest.mark.asyncio
async def test_a_failed_record_write_still_sends_the_final_status():
    client, sender = service_bus()

    async def finish(status, message, with_outputs):
        raise RuntimeError("lease expired")

    with (
        patch.object(
            runner, "build_porter_command", AsyncMock(return_value=([["porter", "install"]], None, "p", None))
        ),
        patch.object(runner, "run_porter", AsyncMock(return_value=(0, "", ""))),
        patch.object(runner, "get_porter_outputs", AsyncMock(return_value=(True, []))),
        patch.object(runner, "logger") as logger,
    ):
        assert await runner.invoke_porter_action(MESSAGE, client, CONFIG, execution_id="run-3", finish=finish)
    assert [body["status"] for body in bodies(sender)] == [
        statuses.in_progress_status_string_for["install"],
        statuses.pass_status_string_for["install"],
    ]
    assert "Could not save the execution record" in logger.error.call_args.args[0]

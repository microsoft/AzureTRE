import asyncio
import os
import signal
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

from helpers.commands import run_command_helper
from vmss_porter.runner import invoke_porter_action


@pytest.mark.asyncio
@pytest.mark.parametrize("ignore_interrupt", [False, True])
async def test_action_child_exits_before_parameter_cleanup(tmp_path, monkeypatch, ignore_interrupt):
    parameter_file = tmp_path / "parameters.json"
    installation_file = tmp_path / "installation.json"
    value_directory = tmp_path / "parameters.json.values"
    value_directory.mkdir(mode=0o700)
    value_file = value_directory / "value"
    for path in (parameter_file, installation_file, value_file):
        path.write_text("synthetic-input")
    ready = tmp_path / "ready"
    interrupted = tmp_path / "interrupted"
    script = """
import signal, sys, time
from pathlib import Path
ready, interrupted, *inputs = map(Path, sys.argv[1:6])
ignore_interrupt = sys.argv[6] == 'True'
def interrupt(signum, frame):
    interrupted.write_text('present' if all(path.exists() for path in inputs) else 'missing')
    if not ignore_interrupt:
        time.sleep(0.1)
        sys.exit(0)
signal.signal(signal.SIGINT, interrupt)
ready.write_text('ready')
while True:
    time.sleep(1)
"""
    command = [
        sys.executable,
        "-c",
        script,
        str(ready),
        str(interrupted),
        str(parameter_file),
        str(installation_file),
        str(value_file),
        str(ignore_interrupt),
    ]
    processes = []
    spawn = asyncio.create_subprocess_exec

    async def capture_process(*args, **kwargs):
        process = await spawn(*args, **kwargs)
        processes.append(process)
        return process

    async def execute(command, *args, **kwargs):
        if command[:3] == ["porter", "parameters", "delete"]:
            assert processes[0].returncode is not None
            assert interrupted.read_text() == "present"
            assert value_file.exists()
            return 0, None, None
        return await run_command_helper(command, *args, **kwargs)

    sender = AsyncMock()
    client = Mock()
    client.get_queue_sender.return_value = sender
    config = {"porter_env": dict(os.environ), "deployment_status_queue": "test"}
    msg = {"id": "test", "action": "install", "operationId": "operation", "stepId": "step"}
    monkeypatch.setattr("helpers.commands._CANCEL_GRACE_PERIOD_SECONDS", 0.3, raising=False)
    with (
        patch("helpers.commands.asyncio.create_subprocess_exec", side_effect=capture_process),
        patch("vmss_porter.runner.azure_login_command", return_value=[]),
        patch("vmss_porter.runner.azure_acr_login_command", return_value=[]),
        patch("vmss_porter.runner.apply_porter_credentials_sets_command", return_value=[]),
        patch(
            "vmss_porter.runner.build_porter_command",
            return_value=([command], str(parameter_file), "test", str(installation_file)),
        ),
        patch("vmss_porter.runner.run_command_helper", side_effect=execute),
    ):
        task = asyncio.create_task(invoke_porter_action(msg, client, config))
        try:

            async def wait_until_ready():
                while not ready.exists():
                    await asyncio.sleep(0.01)

            await asyncio.wait_for(wait_until_ready(), timeout=5)
            task.cancel()
            await asyncio.sleep(0.02)
            task.cancel()  # Repeated cancellation must still wait for the child.
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, timeout=5)
            assert processes[0].returncode == (-signal.SIGKILL if ignore_interrupt else 0)
            assert interrupted.read_text() == "present"
            assert not parameter_file.exists()
            assert not installation_file.exists()
            assert not value_directory.exists()
            assert sender.send_messages.await_count == 1
        finally:
            for process in processes:
                if process.returncode is None:
                    process.kill()
                    await process.wait()
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)

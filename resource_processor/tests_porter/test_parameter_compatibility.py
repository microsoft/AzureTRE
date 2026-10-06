"""Exercise the pinned Porter executable with synthetic bundles and a local MongoDB."""
import base64
import hashlib
import json
import os
import shutil
import subprocess
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import urlsplit
import uuid

import pytest

from helpers.commands import run_command_helper
from vmss_porter.runner import invoke_porter_action


@pytest.fixture
def porter_environment(tmp_path):
    mongo_url = os.environ.get("PORTER_TEST_MONGODB_URL")
    if not mongo_url:
        pytest.skip("Set PORTER_TEST_MONGODB_URL to a disposable local MongoDB database")
    assert urlsplit(mongo_url).hostname in ("127.0.0.1", "localhost"), "Use a disposable local database"
    assert shutil.which("porter"), "Install Porter v1.4.0 to run these tests"
    assert subprocess.check_output(["porter", "version"], text=True, timeout=30).startswith("porter v1.4.0 ")

    porter_home = tmp_path / "porter"
    porter_home.mkdir()
    config = {
        "runtime-driver": "debug",
        "default-storage": "test",
        "default-secrets-plugin": "filesystem",
        "storage": [{"name": "test", "plugin": "mongodb", "config": {"url": mongo_url}}],
    }
    (porter_home / "config.yaml").write_text(json.dumps(config))
    env = dict(os.environ, PORTER_HOME=str(porter_home))
    bundle = {
        "schemaVersion": "v1.0.0", "name": "rp-compatibility", "version": "1.0.0",
        "invocationImages": [{"image": "alpine:latest", "imageType": "docker"}],
        "actions": {"start": {"modifies": True}},
        "parameters": {
            "delete_backups_on_uninstall": {"definition": "boolean", "destination": {"env": "DELETE_BACKUPS"}},
            "rule_collections": {"definition": "string", "destination": {"env": "RULES"}},
            "network_rule_collections": {"definition": "string", "destination": {"env": "NETWORK_RULES"}},
        },
        "definitions": {"boolean": {"type": "boolean", "default": False}, "string": {"type": "string", "default": "old"}},
    }
    bundle_bytes = json.dumps(bundle).encode()
    bundle_path = porter_home / "bundle.json"
    bundle_path.write_bytes(bundle_bytes)

    # Seed Porter's local bundle cache so installation apply needs no registry.
    reference = "example.invalid/rp-compatibility:v1.0.0"
    cache = porter_home / "cache" / hashlib.md5(reference.encode(), usedforsecurity=False).hexdigest()
    (cache / "cnab").mkdir(parents=True)
    (cache / "cnab" / "bundle.json").write_bytes(bundle_bytes)
    (cache / "metadata.json").write_text(json.dumps({
        "reference": reference, "digest": "sha256:" + hashlib.sha256(bundle_bytes).hexdigest()
    }))
    for name in ("arm_auth", "aad_auth"):
        credentials = porter_home / f"{name}.json"
        credentials.write_text(json.dumps({"schemaType": "CredentialSet", "schemaVersion": "1.0.1", "name": name, "credentials": []}))
        subprocess.run(["porter", "credentials", "apply", str(credentials)], env=env, capture_output=True, check=True, timeout=30)
    return env, bundle_path


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["start", "uninstall"])
async def test_legacy_action_is_blocked_then_uses_current_values_after_upgrade(porter_environment, tmp_path, action):
    env, bundle_path = porter_environment
    installation_id = f"rp-compatibility-{uuid.uuid4().hex}"
    initial = subprocess.run([
        "porter", "install", installation_id, "--cnab-file", str(bundle_path),
        "--param", "delete_backups_on_uninstall=true", "--param", "rule_collections=old",
        "--param", "network_rule_collections=old", "--driver", "debug"
    ], env=env, capture_output=True, text=True, check=True, timeout=30)
    assert json.JSONDecoder().raw_decode(initial.stdout[initial.stdout.index("{"):])[0]["action"] == "install"

    parameters = {"delete_backups_on_uninstall": False}
    for name in ("rule_collections", "network_rule_collections"):
        parameters[name] = [{"name": f"workspace-{i}", "rules": ["service.example.com"] * 50} for i in range(200)]
    msg = {
        "id": installation_id, "action": action, "name": "rp-compatibility", "version": "1.0.0",
        "parameters": parameters, "operationId": "test-operation", "stepId": "test-step"
    }
    config = {"registry_server": "example.invalid", "porter_env": env, "deployment_status_queue": "test"}
    sender = AsyncMock()
    client = Mock()
    client.get_queue_sender.return_value = sender
    commands = []
    executions = []

    async def local_command(command, *args, **kwargs):
        commands.append(command)
        if "--reference" in command:
            # Use the synthetic bundle in place of an ACR download for invoke/uninstall.
            command = list(command)
            index = command.index("--reference")
            command[index:index + 2] = ["--cnab-file", str(bundle_path)]
        result = await run_command_helper(command, *args, **kwargs)
        if result[0] == 0 and result[1] and '"installation_name"' in result[1]:
            output = result[1]
            start = output.index('{\n  "installation_name"')
            executions.append(json.JSONDecoder().raw_decode(output[start:])[0])
        return result

    # Only cloud login and registry lookup are replaced. Porter storage and execution are real.
    with patch("helpers.commands.get_porter_parameter_keys", new_callable=AsyncMock, return_value=list(parameters)), \
            patch("vmss_porter.runner.azure_login_command", return_value=[]), \
            patch("vmss_porter.runner.azure_acr_login_command", return_value=[]), \
            patch("vmss_porter.runner.apply_porter_credentials_sets_command", return_value=[]), \
            patch("vmss_porter.runner.run_command_helper", side_effect=local_command), \
            patch("helpers.commands.tempfile.tempdir", str(tmp_path)):
        assert await invoke_porter_action(msg, client, config) is False
        assert executions == []
        assert not any(command[:3] == ["porter", "parameters", "apply"] for command in commands)
        assert "Upgrade this resource" in json.loads(str(sender.send_messages.call_args.args[0]))["message"]
        assert not list(tmp_path.glob("*.json"))

        upgrade = dict(msg, action="upgrade", parameters={"delete_backups_on_uninstall": True, "rule_collections": [], "network_rule_collections": []})
        assert await invoke_porter_action(upgrade, client, config) is True
        assert await invoke_porter_action(msg, client, config) is True

    assert [run["action"] for run in executions] == ["upgrade", action]
    actual = executions[-1]["parameters"]
    assert actual["delete_backups_on_uninstall"] is False
    for name in ("rule_collections", "network_rule_collections"):
        assert len(actual[name]) > 128 * 1024
        assert json.loads(base64.b64decode(actual[name])) == parameters[name]
    assert not list(tmp_path.glob("*.json"))
    assert all("--param" not in command for command in commands)

"""Exercise the pinned Porter executable with synthetic bundles and a local MongoDB."""
import base64
import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import urlsplit
import uuid

import pytest
import yaml

from helpers.commands import run_command_helper
from vmss_porter.runner import invoke_porter_action


@pytest.fixture
def porter_environment(tmp_path):
    mongo_url = os.environ.get("PORTER_TEST_MONGODB_URL")
    if not mongo_url:
        pytest.skip("Set PORTER_TEST_MONGODB_URL to a disposable local MongoDB database")
    assert urlsplit(mongo_url).hostname in ("127.0.0.1", "localhost"), "Use a disposable local database"
    assert shutil.which("porter"), "Install Porter v1.4.0 to run these tests"
    version = subprocess.check_output(["porter", "version"], text=True, timeout=30)
    assert version.startswith("porter v1.4.0 ")

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
            "smtpPassword": {"definition": "password", "destination": {"env": "SMTP_PASSWORD"}},
        },
        "definitions": {"boolean": {"type": "boolean", "default": False}, "string": {"type": "string", "default": "old"},
                        "password": {"type": "string", "writeOnly": True, "default": "old-password"}},
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

    parameters = {"delete_backups_on_uninstall": False, "smtpPassword": "synthetic-secret-never-in-parameter-set"}
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
        if command[:3] == ["porter", "parameters", "apply"] and result[0] == 0:
            document = json.loads(Path(command[3]).read_text())
            stored = subprocess.check_output([
                "porter", "parameters", "show", document["name"], "--output", "json"
            ], env=env, text=True, timeout=30)
            stored_sources = json.loads(stored)["parameters"]
            assert parameters["smtpPassword"] not in stored
            assert all(set(parameter["source"]) == {"path"} for parameter in stored_sources)
            assert all(Path(parameter["source"]["path"]).is_file() for parameter in stored_sources)
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
        blocked_result = await invoke_porter_action(msg, client, config)
        assert blocked_result is False
        assert executions == []
        assert not any(command[:3] == ["porter", "parameters", "apply"] for command in commands)
        assert "Upgrade this resource" in json.loads(str(sender.send_messages.call_args.args[0]))["message"]
        assert not list(tmp_path.glob("*.json*"))

        upgrade = dict(msg, action="upgrade", parameters={
            "delete_backups_on_uninstall": True, "rule_collections": [],
            "network_rule_collections": [], "smtpPassword": "previous-password"
        })
        upgrade_result = await invoke_porter_action(upgrade, client, config)
        assert upgrade_result is True
        action_result = await invoke_porter_action(msg, client, config)
        assert action_result is True

    assert [run["action"] for run in executions] == ["upgrade", action]
    actual = executions[-1]["parameters"]
    assert actual["delete_backups_on_uninstall"] is False
    assert actual["smtpPassword"] == parameters["smtpPassword"]
    for name in ("rule_collections", "network_rule_collections"):
        assert len(actual[name]) > 128 * 1024
        assert json.loads(base64.b64decode(actual[name])) == parameters[name]
    assert not list(tmp_path.glob("*.json*"))
    assert all("--param" not in command for command in commands)


@pytest.mark.asyncio
async def test_large_firewall_parameters_reach_terraform_in_a_linux_container(porter_environment, tmp_path):
    if os.environ.get("PORTER_TEST_CONTAINERS") != "1":
        pytest.skip("Set PORTER_TEST_CONTAINERS=1 to exercise Docker and Terraform")
    env, bundle_path = porter_environment
    firewall = Path(__file__).resolve().parents[2] / "templates" / "shared_services" / "firewall"
    manifest = yaml.safe_load((firewall / "porter.yaml").read_text())
    names = ("rule_collections", "network_rule_collections")
    destinations = {parameter["name"]: parameter["path"] for parameter in manifest["parameters"] if parameter["name"] in names}
    # The real manifest must pass file paths to Terraform for every lifecycle action.
    for action in ("install", "upgrade", "uninstall"):
        variables = manifest[action][0]["terraform"]["vars"]
        for name in names:
            assert variables[f"api_driven_{name}_file"] == "${ bundle.parameters." + name + " }"
        assert not any(name.endswith("_b64") for name in variables)

    context = tmp_path / "container"
    context.mkdir()
    for name in ("variables.tf", "locals.tf"):
        shutil.copyfile(firewall / "terraform" / name, context / name)
    (context / "outputs.tf").write_text('''
output "application_digest" { value = sha256(jsonencode(local.api_driven_application_rule_collection)) }
output "network_digest" { value = sha256(jsonencode(local.api_driven_network_rule_collection)) }
''')
    # Exercise the production Terraform inputs without an Azure provider or backend.
    (context / "run").write_text(
        "#!/bin/sh\nset -eu\ncd /test\nterraform init -backend=false -no-color\n"
        "terraform apply -auto-approve -no-color -var=tre_id=test -var=firewall_policy_id=test "
        + " ".join(f"-var=api_driven_{name}_file={destinations[name]}" for name in names) + "\n")
    (context / "run").chmod(0o755)
    base_image = os.environ.get("PORTER_TEST_TERRAFORM_IMAGE", "hashicorp/terraform:1.14.3")
    (context / "Dockerfile").write_text(f"FROM {base_image}\nUSER 0\nCOPY *.tf /test/\nCOPY run /cnab/app/run\nENTRYPOINT []\nCMD [\"/cnab/app/run\"]\n")
    image_name = f"rp-firewall-compatibility:{uuid.uuid4().hex}"
    subprocess.run(["docker", "build", "--tag", image_name, str(context)],
                   env=dict(os.environ, DOCKER_BUILDKIT="0"), check=True, capture_output=True, timeout=180)
    try:
        bundle = json.loads(bundle_path.read_text())
        bundle["invocationImages"][0]["image"] = image_name
        for name in names:
            bundle["parameters"][name]["destination"] = {"path": destinations[name]}
        bundle_bytes = json.dumps(bundle).encode()
        bundle_path.write_bytes(bundle_bytes)
        cache = next((bundle_path.parent / "cache").iterdir())
        (cache / "cnab" / "bundle.json").write_bytes(bundle_bytes)
        metadata = json.loads((cache / "metadata.json").read_text())
        metadata["digest"] = "sha256:" + hashlib.sha256(bundle_bytes).hexdigest()
        (cache / "metadata.json").write_text(json.dumps(metadata))
        porter_config_path = bundle_path.parent / "config.yaml"
        porter_config = json.loads(porter_config_path.read_text())
        porter_config["runtime-driver"] = "docker"
        porter_config_path.write_text(json.dumps(porter_config))

        parameters = {
            name: [{"name": f"workspace-{i}", "rules": ["service.example.com"] * 50} for i in range(200)]
            for name in names
        }
        expected_digest = hashlib.sha256(json.dumps(parameters[names[0]], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        assert all(len(base64.b64encode(json.dumps(value).encode())) > 128 * 1024 for value in parameters.values())
        passwords = ("synthetic-previous-password", "synthetic-current-password")
        parameters["smtpPassword"] = passwords[0]
        msg = {"id": f"rp-files-{uuid.uuid4().hex}", "name": "rp-compatibility", "version": "1.0.0",
               "parameters": parameters, "operationId": "test-operation", "stepId": "test-step"}
        config = {"registry_server": "example.invalid", "porter_env": env, "deployment_status_queue": "test"}
        sender = AsyncMock()
        client = Mock()
        client.get_queue_sender.return_value = sender
        outputs = []

        async def local_command(command, *args, **kwargs):
            if "--reference" in command:
                command = list(command)
                index = command.index("--reference")
                command[index:index + 2] = ["--cnab-file", str(bundle_path)]
            result = await run_command_helper(command, *args, **kwargs)
            if command[:3] == ["porter", "installation", "apply"] or command[:2] == ["porter", "uninstall"]:
                assert result[0] == 0, result[2]
                for password in passwords:
                    assert password not in (result[1] or "") + (result[2] or "")
                outputs.append(result[1])
            return result

        with patch("helpers.commands.get_porter_parameter_keys", new_callable=AsyncMock, return_value=list(parameters)), \
                patch("vmss_porter.runner.azure_login_command", return_value=[]), \
                patch("vmss_porter.runner.azure_acr_login_command", return_value=[]), \
                patch("vmss_porter.runner.apply_porter_credentials_sets_command", return_value=[]), \
                patch("vmss_porter.runner.run_command_helper", side_effect=local_command), \
                patch("helpers.commands.tempfile.tempdir", str(tmp_path)):
            for action in ("install", "upgrade", "uninstall"):
                if action == "upgrade":
                    parameters["smtpPassword"] = passwords[1]
                result = await invoke_porter_action(dict(msg, action=action), client, config)
                assert result is True
        assert len(outputs) == 3
        for output in outputs:
            assert f'application_digest = "{expected_digest}"' in output
            assert f'network_digest = "{expected_digest}"' in output
        assert not list(tmp_path.glob("*.json*"))
    finally:
        subprocess.run(["docker", "image", "rm", image_name], capture_output=True, check=True, timeout=30)


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["install", "upgrade", "start", "uninstall"])
async def test_cancellation_waits_for_docker_invocation_before_cleanup(porter_environment, tmp_path, monkeypatch, action):
    if os.environ.get("PORTER_TEST_CONTAINERS") != "1":
        pytest.skip("Set PORTER_TEST_CONTAINERS=1 to exercise Docker")
    env, bundle_path = porter_environment
    identifier = uuid.uuid4().hex
    image_name = f"rp-cancellation:{identifier}"
    label = f"rp-cancellation={identifier}"
    context = tmp_path / "container"
    context.mkdir()
    (context / "run").write_text("#!/bin/sh\nset -eu\nwhile [ ! -f /finished ]; do sleep 0.1; done\n")
    (context / "run").chmod(0o755)
    base_image = os.environ.get("PORTER_TEST_TERRAFORM_IMAGE", "hashicorp/terraform:1.14.3")
    (context / "Dockerfile").write_text(
        f"FROM {base_image}\nUSER 0\nLABEL {label}\nCOPY run /cnab/app/run\nENTRYPOINT []\n")
    subprocess.run(["docker", "build", "--tag", image_name, str(context)],
                   env=dict(os.environ, DOCKER_BUILDKIT="0"), check=True, capture_output=True, timeout=180)
    task = None

    def containers():
        return subprocess.check_output(["docker", "ps", "-aq", "--filter", f"label={label}"], text=True, timeout=15).split()

    try:
        bundle = json.loads(bundle_path.read_text())
        bundle["invocationImages"][0]["image"] = image_name
        bundle_bytes = json.dumps(bundle).encode()
        bundle_path.write_bytes(bundle_bytes)
        cache = next((bundle_path.parent / "cache").iterdir())
        (cache / "cnab" / "bundle.json").write_bytes(bundle_bytes)
        metadata = json.loads((cache / "metadata.json").read_text())
        metadata["digest"] = "sha256:" + hashlib.sha256(bundle_bytes).hexdigest()
        (cache / "metadata.json").write_text(json.dumps(metadata))
        config_path = bundle_path.parent / "config.yaml"
        porter_config = json.loads(config_path.read_text())
        config = {"registry_server": "example.invalid", "porter_env": env, "deployment_status_queue": "test"}
        msg = {"id": f"rp-cancel-{identifier}", "action": action, "name": "rp-compatibility", "version": "1.0.0",
               "parameters": {"smtpPassword": "synthetic-secret"}, "operationId": "operation", "stepId": "step"}
        sender = AsyncMock()
        client = Mock()
        client.get_queue_sender.return_value = sender
        monkeypatch.setattr("helpers.commands._CANCEL_GRACE_PERIOD_SECONDS", 0.1)

        async def local_command(command, *args, **kwargs):
            if "--reference" in command:
                command = list(command)
                index = command.index("--reference")
                command[index:index + 2] = ["--cnab-file", str(bundle_path)]
            return await run_command_helper(command, *args, **kwargs)

        with patch("helpers.commands.get_porter_parameter_keys", return_value=["smtpPassword"]), \
                patch("vmss_porter.runner.azure_login_command", return_value=[]), \
                patch("vmss_porter.runner.azure_acr_login_command", return_value=[]), \
                patch("vmss_porter.runner.apply_porter_credentials_sets_command", return_value=[]), \
                patch("vmss_porter.runner.run_command_helper", side_effect=local_command), \
                patch("helpers.commands.tempfile.tempdir", str(tmp_path)):
            if action != "install":
                installed = await invoke_porter_action(dict(msg, action="install"), client, config)
                assert installed is True
                sender.reset_mock()
            porter_config["runtime-driver"] = "docker"
            config_path.write_text(json.dumps(porter_config))
            task = asyncio.create_task(invoke_porter_action(msg, client, config))

            async def wait_for_invocation():
                while True:
                    candidates = await asyncio.to_thread(containers)
                    if candidates:
                        return candidates[0]
                    if task.done():
                        raise AssertionError(f"Porter exited before starting a container: {task.result()}")
                    await asyncio.sleep(0.05)

            container = await asyncio.wait_for(wait_for_invocation(), timeout=15)
            task.cancel()
            await asyncio.sleep(0.2)
            task.cancel()
            await asyncio.sleep(0.2)
            assert not task.done(), "Cancellation must wait for the Docker invocation to finish"
            assert list(tmp_path.glob("*.json.values/*")), "Keep parameter inputs until execution finishes"
            await asyncio.to_thread(subprocess.run, ["docker", "exec", container, "touch", "/finished"],
                                    check=True, capture_output=True, timeout=15)
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, timeout=15)
        assert containers() == [], "Porter must remove its completed invocation container before cancellation returns"
        assert not list(tmp_path.glob("*.json*"))
        assert sender.send_messages.await_count == 1
    finally:
        for container in containers():
            subprocess.run(["docker", "rm", "-f", container], check=True, capture_output=True, timeout=15)
        if task is not None:
            if not task.done():
                task.cancel()
            await asyncio.wait_for(asyncio.gather(task, return_exceptions=True), timeout=15)
        subprocess.run(["docker", "image", "rm", image_name], capture_output=True, check=True, timeout=30)

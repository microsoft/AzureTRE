import sys
from typing import Union
import click
import json
import msal
import os

from httpx import Client, Response
from logging import Logger
from pathlib import Path

from tre.authentication import get_auth_token_client_credentials, get_public_client_application


class ApiException(click.ClickException):
    """An exception that Click can handle and show to the user containing API call error info."""

    # Use exit code 2 for API errors that are JSON
    exit_code = 2

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def show(self, file=None) -> None:
        # Write (JSON) message stdout without any extra info to allow callers to parse it
        click.echo(self.message, file=file)


class ApiClient:
    def __init__(self,
                 base_url: str,
                 verify: bool):
        self.base_url = base_url
        self.verify = verify

    @staticmethod
    def get_api_client_from_config() -> "ApiClient":

        config_path = Path("~/.config/tre/environment.json").expanduser()
        if not config_path.exists():
            raise click.ClickException(
                "You need to log in (tre login) before calling this command"
            )

        config_text = config_path.read_text(encoding="utf-8")
        config = json.loads(config_text)

        if os.getenv("TRECLI_BASE_URL"):
            base_url = os.getenv("TRECLI_BASE_URL")
            click.echo(f"Using API base URL '{base_url}' (overridden by TRECLI_BASE_URL)", err=True)
        else:
            base_url = config["base-url"]

        login_method = config["login-method"]
        if login_method == "client-credentials":
            return ClientCredentialsApiClient(
                base_url,
                config["verify"],
                config["client-id"],
                config["client-secret"],
                config["aad-tenant-id"],
                config["api-scope"]
            )
        elif login_method == "device-code":
            return DeviceCodeApiClient(
                base_url,
                config["verify"],
                config["token-cache-file"],
                config["client-id"],
                config["aad-tenant-id"],
                config["api-scope"]
            )
        else:
            raise click.ClickException(f"Unhandled login method: {login_method}")

    @staticmethod
    def get_api_metadata(api_base_url: str) -> "Union[dict[str, str], None]":
        with Client() as client:
            url = f"{api_base_url}/api/.metadata"

            response = client.get(url)
            if response.status_code == 200:
                response_json = response.json()
                return response_json
            else:
                return None

    def call_api(
        self,
        log: Logger,
        method: str,
        url: str,
        headers: "dict[str, str]" = {},
        json_data=None,
        scope_id: str = None,
        throw_on_error: bool = True,
        params: "Union[dict[str, str], None]" = None
    ) -> Response:
        with Client(verify=self.verify) as client:
            headers = headers.copy()
            headers['Authorization'] = f"Bearer {self.get_auth_token(log, scope_id)}"
            response = client.request(method, f'{self.base_url}{url}', headers=headers, json=json_data, params=params)
            if throw_on_error and response.is_error:
                error_info = {
                    'status_code': response.status_code,
                    'body': response.text,
                }
                raise ApiException(message=json.dumps(error_info, indent=2))
            return response

    def get_workspace_scope(self, log, workspace_id: str) -> str:
        workspace_response = self.call_api(
            log,
            "GET",
            f'/api/workspaces/{workspace_id}',
        )
        workspace_json = workspace_response.json()
        workspace_scope = workspace_json["workspace"]["properties"]["scope_id"]
        return workspace_scope

    def get_auth_token() -> str:
        pass


class ClientCredentialsApiClient(ApiClient):
    def __init__(self,
                 base_url: str,
                 verify: bool,
                 client_id: str,
                 client_secret: str,
                 aad_tenant_id: str,
                 scope: str):
        while base_url.endswith("/"):
            base_url = base_url[0:-1]
        super().__init__(base_url, verify)
        self._client_id = client_id
        self._client_secret = client_secret
        self._aad_tenant_id = aad_tenant_id
        self._scope = scope

    def get_auth_token(self, log, scope):
        return get_auth_token_client_credentials(log, self._client_id, self._client_secret, self._aad_tenant_id, scope or self._scope, self.verify)


class DeviceCodeApiClient(ApiClient):
    def __init__(self,
                 base_url: str,
                 verify: bool,
                 token_cache_file: str,
                 client_id: str,
                 aad_tenant_id: str,
                 scope: str):
        super().__init__(base_url, verify)
        self._token_cache_file = token_cache_file
        self._client_id = client_id
        self._aad_tenant_id = aad_tenant_id
        self._scope = scope

    def get_auth_token(self, log, scope):

        effective_scope = scope or self._scope

        cache = msal.SerializableTokenCache()
        if os.path.exists(self._token_cache_file):
            cache.deserialize(open(self._token_cache_file, "r").read())

        app = get_public_client_application(self._client_id, self._aad_tenant_id, cache)

        accounts = app.get_accounts()
        if accounts:
            auth_result = app.acquire_token_silent(scopes=[effective_scope], account=accounts[0])
            try:
                auth_result = app.acquire_token_silent(scopes=[effective_scope], account=accounts[0])
            except Exception:
                auth_result = app.acquire_token_for_client(scopes=[effective_scope])
            if cache.has_state_changed:
                with open(self._token_cache_file, "w") as cache_file:
                    cache_file.write(cache.serialize())
            if auth_result is not None:
                if "access_token" in auth_result:
                    token = auth_result["access_token"]
                    return token
                else:
                    raise click.ClickException(f"Failed to get access_token: ${str(auth_result)}")

        if sys.stdin.isatty() or sys.stdout.isatty():
            # We have TTY - try interactive acquire :-)
            click.echo(f"No cached token - initiating device code flow for scope '{effective_scope}'", err=True)
            flow = app.initiate_device_flow(scopes=[effective_scope])
            if "user_code" not in flow:
                raise click.ClickException("unable to initiate device flow")

            click.echo(flow['message'], err=True)
            auth_result = app.acquire_token_by_device_flow(flow)

            if cache.has_state_changed:
                with open(self._token_cache_file, "w") as cache_file:
                    cache_file.write(cache.serialize())
            if auth_result is not None:
                if "access_token" in auth_result:
                    token = auth_result["access_token"]
                    return token
                else:
                    raise click.ClickException(f"Failed to get access_token: ${str(auth_result)}")

        raise RuntimeError(f"Failed to get auth token for scope '{scope}'")

    def get_workspace_scope(self, log, workspace_id: str) -> str:
        # device code flow wants "/user_impersonation" suffix, but client creds doesn't
        # Override here to append
        workspace_scope = super().get_workspace_scope(log, workspace_id)
        return workspace_scope + "/user_impersonation"

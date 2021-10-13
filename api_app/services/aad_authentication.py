import base64
import logging
import jwt
import requests
import rsa

from fastapi import Request, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer

from core import config
from models.domain.authentication import User
from services.aad_access_service import AADAccessService
from resources import strings
from api.dependencies.database import get_db_client_from_request
from db.repositories.workspaces import WorkspaceRepository


class AzureADAuthorization(OAuth2AuthorizationCodeBearer):
    _jwt_keys: dict = {}

    _default_app_reg_id = None
    def __init__(self, aad_instance: str, aad_tenant: str, auto_error: bool = True, app_reg_id: str = None):
        super(AzureADAuthorization, self).__init__(
            authorizationUrl=f"{aad_instance}/{aad_tenant}/oauth2/v2.0/authorize",
            tokenUrl=f"{aad_instance}/{aad_tenant}/oauth2/v2.0/token",
            refreshUrl=f"{aad_instance}/{aad_tenant}/oauth2/v2.0/token",
            scheme_name="oauth2", scopes={
                f"api://{config.API_CLIENT_ID}/Workspace.Read": "List and Get TRE Workspaces",
                f"api://{config.API_CLIENT_ID}/Workspace.Write": "Modify TRE Workspaces"
            },
            auto_error=auto_error
        )
        logging.debug("default app registration id set to: %s", app_reg_id)
        self._default_app_reg_id = app_reg_id

    async def __call__(self, request: Request) -> User:
        token: str = await super(AzureADAuthorization, self).__call__(request)

        try:
            app_reg_id = self._default_app_reg_id

            # if an app reg id was not given, it means we need to fetch it, based on the given workspace id
            if self._default_app_reg_id is None:
                logging.info("Default workspace app registration was not provided. Translating from workspace ID")
                app_reg_id = self._fetch_ws_app_reg_id_from_ws_id(request)

            decoded_token = self._decode_token(token, app_reg_id)
        except Exception as e:
            logging.debug(e)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=strings.AUTH_UNABLE_TO_VALIDATE_TOKEN, headers={"WWW-Authenticate": "Bearer"})

        try:
            return self._get_user_from_token(decoded_token)
        except Exception as e:
            logging.debug(e)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=strings.AUTH_COULD_NOT_VALIDATE_CREDENTIALS, headers={"WWW-Authenticate": "Bearer"})

    @staticmethod
    def _fetch_ws_app_reg_id_from_ws_id(request: Request) -> str:
        workspace_id = None
        if "workspace_id" not in request.path_params:
            logging.error("Neither a workspace ID nor a default app registration id were provided")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=strings.AUTH_COULD_NOT_VALIDATE_CREDENTIALS)
        try:
            workspace_id = request.path_params['workspace_id']
            ws_repo = WorkspaceRepository(get_db_client_from_request(request))
            workspace = ws_repo.get_workspace_by_id(workspace_id)
            ws_app_reg_id = workspace.authInformation['sp_id']

            return ws_app_reg_id
        except Exception as e:
            logging.error(e)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=strings.AUTH_COULD_NOT_VALIDATE_CREDENTIALS)


    @staticmethod
    def _get_user_from_token(decoded_token: dict) -> User:
        user_id = decoded_token['oid']
        access_service = AADAccessService()
        role_assignments = access_service.get_user_role_assignments(user_id)

        return User(id=user_id,
                    name=decoded_token.get('name', ''),
                    email=decoded_token.get('email', ''),
                    roles=decoded_token.get('roles', []),
                    roleAssignments=role_assignments)

    def _decode_token(self, token: str, ws_app_reg_id: str) -> dict:
        key_id = self._get_key_id(token)
        key = self._get_token_key(key_id)

        logging.debug("workspace app registration id: %s", ws_app_reg_id)
        return jwt.decode(token, key, algorithms=['RS256'], audience=ws_app_reg_id)

    @staticmethod
    def _get_key_id(token: str) -> str:
        headers = jwt.get_unverified_header(token)
        return headers['kid'] if headers and 'kid' in headers else None

    @staticmethod
    def _ensure_b64padding(key: str) -> str:
        """
        The base64 encoded keys are not always correctly padded, so pad with the right number of =
        """
        key = key.encode('utf-8')
        missing_padding = len(key) % 4
        for _ in range(missing_padding):
            key = key + b'='
        return key

    def _get_token_key(self, key_id: str) -> str:
        """
        Rather tha use PyJWKClient.get_signing_key_from_jwt every time, we'll get all the keys from AAD and cache them.
        """
        if key_id not in AzureADAuthorization._jwt_keys:
            response = requests.get(f"{config.AAD_INSTANCE}/{config.AAD_TENANT_ID}/v2.0/.well-known/openid-configuration")
            aad_metadata = response.json() if response.ok else None
            jwks_uri = aad_metadata['jwks_uri'] if aad_metadata and 'jwks_uri' in aad_metadata else None
            if jwks_uri:
                response = requests.get(jwks_uri)
                keys = response.json() if response.ok else None
                if keys and 'keys' in keys:
                    for key in keys['keys']:
                        n = int.from_bytes(base64.urlsafe_b64decode(self._ensure_b64padding(key['n'])), "big")
                        e = int.from_bytes(base64.urlsafe_b64decode(self._ensure_b64padding(key['e'])), "big")
                        pub_key = rsa.PublicKey(n, e)
                        # Cache the PEM formatted public key.
                        AzureADAuthorization._jwt_keys[key['kid']] = pub_key.save_pkcs1()

        return AzureADAuthorization._jwt_keys[key_id]


authorize_tre_app = \
    AzureADAuthorization(config.AAD_INSTANCE, config.AAD_TENANT_ID, True, config.API_AUDIENCE)
authorize_ws_app = AzureADAuthorization(config.AAD_INSTANCE, config.AAD_TENANT_ID)

from fastapi import Request, Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer, HTTPBearer
from typing import List, Optional
from core import config
import base64
import jwt
import requests
import rsa

class User:
    def __init__(self, decoded_token: dict):
        self._claims = decoded_token

    @property
    def id(self):
        return self._get_claim('oid')

    @property
    def name(self):
        return self._get_claim('name')

    @property
    def email(self):
        return self._get_claim('email')

    @property
    def roles(self):
        return self._get_claim('roles')

    def _get_claim(self, claim: str):
        if claim in self._claims:
            return self._claims[claim]

class AzureADAuthorization(OAuth2AuthorizationCodeBearer):
    _jwt_keys: dict = {}

    def __init__(
        self,
        instance: str,
        tenant: str,
        auto_error: bool = True,
    ):
        super(AzureADAuthorization, self).__init__(
            authorizationUrl = "{instance}/{tenant}/oauth2/v2.0/authorize".format(tenant=tenant,instance=instance),
            tokenUrl = "{instance}/{tenant}/oauth2/v2.0/token".format(tenant=tenant,instance=instance),
            refreshUrl = "{instance}/{tenant}/oauth2/v2.0/token".format(tenant=tenant,instance=instance),
            scheme_name="oauth2",
            scopes={
                "api://{}/user_impersonation".format(config.API_CLIENT_ID): "Access TRE API"
            },
            auto_error=auto_error
        )

    async def __call__(self, request: Request, required_roles: Optional[List[str]] = []) -> User:
        token: str = await super(AzureADAuthorization, self).__call__(request)

        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            decoded_token = self._validate_token(token)

            if 'roles' not in decoded_token or len(decoded_token['roles']) == 0:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not assigned to any role.")

            return User(decoded_token)
        except:
            raise credentials_exception


    def _validate_token(self, token: str):
        key_id = self._get_key_id(token)

        key = self._get_token_key(key_id)

        decoded  = jwt.decode(token, key, verify=True, algorithms=['RS256'], audience=config.API_AUDIENCE)

        return decoded

    def _get_key_id(self, token: str):
        headers = jwt.get_unverified_header(token)
        if headers and 'kid' in headers:
            kid = headers['kid']
        return kid

    # The base64 encoded keys are not always correctly padded, so pad with the right number of =
    def _ensure_b64padding(self, key: str):
        key = key.encode('utf-8')
        missing_padding = len(key) % 4
        for _ in range(missing_padding):
            key = key + b'='
        return key

    # Rather tha use PyJWKClient.get_signing_key_from_jwt every time, we'll get all the keys from AAD and cache them.
    def _get_token_key(self, key_id: str):
        if not key_id in self._jwt_keys:
            resp = requests.get("{instance}/{tenant}/v2.0/.well-known/openid-configuration".format(tenant=config.TENANT_ID,instance=config.AAD_INSTANCE))

            if resp.ok:
                aad_metadata = resp.json()
            if aad_metadata and 'jwks_uri' in aad_metadata:
                jwks_uri = aad_metadata['jwks_uri']

            if jwks_uri:
                resp = requests.get(jwks_uri)
                if resp.ok:
                    keys = resp.json()
                if keys and 'keys' in keys:
                    for key in keys['keys']:
                        n = int.from_bytes(base64.urlsafe_b64decode(self._ensure_b64padding(key['n'])), "big")
                        e = int.from_bytes(base64.urlsafe_b64decode(self._ensure_b64padding(key['e'])), "big")
                        pub_key = rsa.PublicKey(n, e)
                        # Cache the PEM formatted public key.
                        self._jwt_keys[key['kid']] = pub_key.save_pkcs1()

        return self._jwt_keys[key_id]

authorize = AzureADAuthorization(config.AAD_INSTANCE, config.TENANT_ID)

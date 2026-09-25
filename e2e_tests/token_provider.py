from azure.core.credentials import TokenCredential


class TokenProvider:
    """Keep the credential and scope so Azure Identity can renew cached tokens."""

    def __init__(self, credential: TokenCredential, scope: str):
        self._credential = credential
        self._scope = scope

    def get_token(self) -> str:
        # Call for each request. The credential handles caching and expiry.
        return self._credential.get_token(self._scope).token

"""Check identity TLS at the real SDK transport without making network requests."""

import os
import unittest
from unittest.mock import patch

from azure.core.exceptions import ClientAuthenticationError

from e2e_tests import helpers


class OfflineTransportReached(Exception):
    pass


class IdentityTlsTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(
            patch.multiple(
                helpers.config,
                AAD_TENANT_ID="tenant",
                TEST_ACCOUNT_CLIENT_ID="client",
                TEST_ACCOUNT_CLIENT_SECRET="dummy-secret",
                TEST_APP_ID="app",
                TEST_USER_NAME="user",
                TEST_USER_PASSWORD="dummy-password",
            )
        )
        self.enterContext(
            patch.object(helpers.cloud, "get_aad_authority_fqdn", return_value="login.microsoftonline.com")
        )

    def check_identity_tls(self):
        for tre_verify in (True, False):
            for ca_bundle in ("", "/configured/identity-ca.pem"):
                with (
                    self.subTest(tre_verify=tre_verify, ca_bundle=ca_bundle),
                    patch.dict(os.environ, {"REQUESTS_CA_BUNDLE": ca_bundle, "CURL_CA_BUNDLE": ""}),
                    patch(
                        "requests.adapters.HTTPAdapter.send",
                        side_effect=OfflineTransportReached("offline identity TLS test"),
                    ) as send,
                ):
                    provider = helpers.get_token("api://workspace", verify=tre_verify)
                    try:
                        # Let Azure Identity and Requests resolve the transport settings.
                        # Stop before the adapter opens a connection or validates the CA file.
                        with self.assertRaisesRegex(ClientAuthenticationError, "offline identity TLS test"):
                            provider.get_token()
                        send.assert_called_once()
                        self.assertTrue(send.call_args.args[0].url.startswith("https://login.microsoftonline.com/"))
                        self.assertEqual(send.call_args.kwargs["verify"], ca_bundle or True)
                    finally:
                        provider._credential.close()

    def test_client_credentials_verify_identity_tls_independently_of_tre(self):
        self.check_identity_tls()

    def test_password_credentials_verify_identity_tls_independently_of_tre(self):
        with patch.multiple(helpers.config, TEST_ACCOUNT_CLIENT_ID="", TEST_ACCOUNT_CLIENT_SECRET=""):
            self.check_identity_tls()

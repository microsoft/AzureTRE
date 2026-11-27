"""Make sure that the seed workspace of an upgrade check is a workspace that the test identity created."""

import base64
import json

from e2e_tests import config
from e2e_tests.resources import strings
from e2e_tests.token_provider import TokenProvider


def token_object_id(token):
    """Return the oid claim of a token, or None. The API stores this claim as the user ID of a new resource."""
    if isinstance(token, TokenProvider):
        token = token.get_token()
    try:
        encoded = token.split(".")[1]
        object_id = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))["oid"]
    except (ValueError, IndexError, KeyError, TypeError, AttributeError):
        return None
    return object_id if isinstance(object_id, str) and object_id else None


def require_own_seed(seed, admin_token):
    """Stop before the first change if the test identity did not create the workspace with the seed name.

    A verify case disables and deletes its seed workspace, and the display name of a workspace is not unique.
    Each seed case creates a base workspace with the manual test workspace application, and the API records the
    test identity as the user of that workspace.
    """
    no_change = f"The case made no change to workspace {seed['id']}."
    test_identity = token_object_id(admin_token)
    # Without this stop, a token without the claim is equal to a workspace without a user.
    if test_identity is None:
        raise ValueError(
            f"The admin token has no oid claim, so the case cannot check who created the seed. {no_change}"
        )
    expected = {
        "templateName": (seed["templateName"], strings.BASE_WORKSPACE),
        "properties.client_id": (seed["properties"].get("client_id"), config.TEST_WORKSPACE_APP_ID),
        "user.id": ((seed.get("user") or {}).get("id"), test_identity),
    }
    different = [name for name, (found, wanted) in expected.items() if found != wanted]
    if different:
        raise ValueError(
            "A workspace has the seed name, but the test identity did not create it as a seed: "
            f"{', '.join(different)} is different. {no_change}"
        )

# E2E helper unit tests

Run these tests from the repository root in a Python 3.12 virtual environment:

```bash
python -m pip install -r e2e_tests/unit_tests/requirements.txt
PYTHONPATH=.:e2e_tests python -m unittest discover -s e2e_tests/unit_tests -v
```

The tests use an in-memory HTTP transport and simulated token expiry. They need
no Azure credentials and do not create resources or wait for real token expiry.
They exercise deployment, update and teardown polling, separate Airlock polling
credentials, and authentication failures without replaying resource mutations.

The E2E helpers retain the Azure Identity credential and scope. Each request
asks that credential for a token so the SDK can use its cache or renew an expiring
token. Literal token strings remain supported but cannot be renewed.

These tests check the request and renewal behaviour locally. A live extended
test run is still needed to validate the fix against Azure.

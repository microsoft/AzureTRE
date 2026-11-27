# E2E helper unit tests

Run these tests from the repository root in a Python 3.12 virtual environment:

```bash
python -m pip install -r e2e_tests/unit_tests/requirements.txt
PYTHONPATH=.:e2e_tests python -m unittest discover -s e2e_tests/unit_tests -v
```

These unit tests check the code used by the E2E test suite.
They cover authentication, operation polling, cleanup, timeouts, test selection and result reporting.

They run without Azure credentials or deployed resources.
`test_azure_monitor_contract.py` reads the Azure Monitor Terraform of the core and the base workspace. It makes sure of the order of the private link scope changes and the private endpoint.
Cases named after SQL, Nexus or certificates check the E2E setup, validation and cleanup for those cases.

The tests stay beside the E2E helpers they exercise.
Live E2E tests are still required to validate deployment behaviour against Azure.

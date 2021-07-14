# Testing

## Unit tests

The unit tests are written with pytest and located in folders:

- [Management API](../management_api_app/README.md) unit tests: `/management_api_app/tests_ma/`
- [Resource Processor Function](../processor_function/README.md) unit tests: `/processor_function/tests_pf/`

> The folders containing the unit tests cannot have the same name. Otherwise, pytest will get confused, when trying to run all tests in the root folder.

Run all unit tests with the following command in the root folder of the repository:

```cmd
pytest --ignore=e2e_tests
```

## End-to-end tests

The end-to-end tests are implemented in `/e2e_tests/` folder and can be run with command:

```cmd
pytest e2e_tests
```

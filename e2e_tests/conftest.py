def pytest_addoption(parser):
    parser.addoption("--verify", action="store", default="true")

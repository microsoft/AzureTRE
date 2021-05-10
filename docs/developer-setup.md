# Developer Setup

## Install pre-commit hooks for python

Pre commit hooks help you lint your python code on each git commit, to avoid having to fail the build when submitting a PR. Installing pre-commit hooks is completely optional.

1. Install flake8, pre-commit etc.

    ```cmd
    pip install -r requirements.txt
    ```

2. Enable pre-commit hooks

    ```cmd
    pre-commit install
    ```

import re
from pathlib import Path
import pytest

# Match variable names that indicate secret values but avoid matching common id fields like *_id
SECRET_NAME_RE = re.compile(r"(?i)(secret|client_secret|password|_key|auth_client_secret|client_secret)")
VARIABLE_BLOCK_RE = re.compile(r'variable\s+"(?P<name>[^\"]+)"\s*\{(?P<body>.*?)\}', re.DOTALL)
SENSITIVE_RE = re.compile(r'sensitive\s*=\s*true', re.IGNORECASE)


def has_uncommented_sensitive(body: str) -> bool:
    # Remove block comments
    body_no_block = re.sub(r'/\*.*?\*/', '', body, flags=re.DOTALL)
    # Remove line comments starting with # or //
    body_no_line_comments = re.sub(r'(?m)#.*$', '', body_no_block)
    body_no_line_comments = re.sub(r'(?m)//.*$', '', body_no_line_comments)
    return bool(SENSITIVE_RE.search(body_no_line_comments))


def find_terraform_variable_blocks(root: Path):
    for tf_file in root.glob('templates/**/terraform/*.tf'):
        try:
            text = tf_file.read_text()
        except Exception:
            continue
        for m in VARIABLE_BLOCK_RE.finditer(text):
            yield tf_file, m.group('name'), m.group('body')


def test_secret_named_variables_are_sensitive():
    repo_root = Path.cwd()
    failures = []

    for tf_file, name, body in find_terraform_variable_blocks(repo_root):
        if SECRET_NAME_RE.search(name):
            if not has_uncommented_sensitive(body):
                failures.append(f"{tf_file}: variable '{name}' missing 'sensitive = true'")

    if failures:
        pytest.fail("Found secret-like Terraform variables without sensitive=true:\n" + "\n".join(failures))

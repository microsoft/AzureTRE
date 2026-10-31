"""Make sure that the template shell scripts do not trace their commands."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
# The arguments of each set command, up to a comment or the next command on the line.
SET = re.compile(r"^\s*set\s+([^\n#;]*)", re.MULTILINE)


def turns_on_trace(text):
    for match in SET.finditer(text):
        args = match.group(1).split()
        for index, arg in enumerate(args):
            if arg == "--":
                break
            if re.fullmatch(r"-[a-zA-Z]*x[a-zA-Z]*", arg) or (
                arg == "-o" and args[index + 1 : index + 2] == ["xtrace"]
            ):
                return True
    return False


class TemplateScriptTests(unittest.TestCase):
    def test_trace_forms(self):
        for line in (
            "set -x",
            "set -euxo pipefail",
            "set -o xtrace",
            "set -e -x",
            "set -eu -o xtrace",
            "  set -o errexit -o xtrace",
        ):
            with self.subTest(line=line):
                self.assertTrue(turns_on_trace(line))
        for line in (
            "set +x",
            "set -euo pipefail",
            "set -o pipefail",
            "# set -o xtrace",
            "set -e # -x",
            "set -e; echo -x",
            "set -- -x",
        ):
            with self.subTest(line=line):
                self.assertFalse(turns_on_trace(line))

    def test_scripts_do_not_trace_commands(self):
        scripts = sorted((ROOT / "templates").rglob("*.sh"))
        self.assertTrue(scripts)
        for script in scripts:
            with self.subTest(script=str(script.relative_to(ROOT))):
                self.assertFalse(turns_on_trace(script.read_text()))


if __name__ == "__main__":
    unittest.main()

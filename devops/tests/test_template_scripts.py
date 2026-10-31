"""Make sure that the template shell scripts do not trace their commands."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
# The arguments of each set command, also after a separator or a keyword, up to a comment or the next command.
SET = re.compile(r"(?:^|[;&|]|\bthen\b|\bdo\b|\belse\b)[ \t]*set[ \t]+([^\n#;&|]*)", re.MULTILINE)
# A shebang line with a flag group that contains x.
SHEBANG = re.compile(r"\A#![^\n]*[ \t]-[a-zA-Z]*x")


def turns_on_trace(text):
    if SHEBANG.search(text):
        return True
    for match in SET.finditer(text):
        args = match.group(1).split()
        for index, arg in enumerate(args):
            if arg == "--":
                break
            if re.fullmatch(r"-[a-zA-Z]*x[a-zA-Z]*", arg) or (
                re.fullmatch(r"-[a-zA-Z]*o", arg) and args[index + 1 : index + 2] == ["xtrace"]
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
            "set -euo xtrace",
            "set -o pipefail; set -x",
            "if true; then set -x; fi",
            "true && set -x",
            "#!/bin/bash -x\necho done",
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
            "set -e; tar -xzf a.tgz",
            "echo reset -x",
            "#!/bin/bash\nset -e",
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

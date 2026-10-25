"""Make sure that the template shell scripts do not trace their commands."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
TRACE = re.compile(r"^\s*set\s+(-[a-zA-Z]*x[a-zA-Z]*|-o\s+xtrace)\b", re.MULTILINE)


class TemplateScriptTests(unittest.TestCase):
    def test_scripts_do_not_trace_commands(self):
        scripts = sorted((ROOT / "templates").rglob("*.sh"))
        self.assertTrue(scripts)
        for script in scripts:
            with self.subTest(script=str(script.relative_to(ROOT))):
                self.assertIsNone(TRACE.search(script.read_text()))


if __name__ == "__main__":
    unittest.main()

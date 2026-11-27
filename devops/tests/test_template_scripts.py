"""Make sure that the template shell scripts do not trace their commands."""

from pathlib import Path
import re
import shlex
import unittest


ROOT = Path(__file__).resolve().parents[2]
# A shebang line with a flag group that contains x.
SHEBANG = re.compile(r"\A#![^\n]*[ \t]-[a-zA-Z]*x")
# Words after which the next word is a command.
SEPARATORS = {";", "&", "&&", "|", "||", "|&", "(", ")", ";;"}
KEYWORDS = {"if", "then", "elif", "else", "do", "while", "until", "!", "{", "}"}


def words(line):
    """The words of one line, with their quotes, so that a quoted or escaped separator stays a word."""
    lexer = shlex.shlex(line, posix=False, punctuation_chars=";&|()")
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:
        # An open quote, for example in the text of a here-document. Read the plain words.
        return re.findall(r"[;&|()]+|[^\s;&|()]+", re.sub(r"(^|\s)#.*", "", line))


def unquoted(word):
    """A word without the quotes around it, as the shell gives it to the command."""
    if len(word) >= 2 and word[0] == word[-1] and word[0] in "'\"":
        return word[1:-1]
    return word


def set_arguments(text):
    """The arguments of each set command that the shell runs."""
    for line in text.splitlines():
        command_start, args, after_backslash = True, None, False
        for raw in words(line) + [";"]:
            # A quoted separator keeps its quotes. An escaped one, as in "find -exec ... \\;", follows a backslash.
            separator = raw in SEPARATORS and not after_backslash
            after_backslash = raw == "\\"
            word = unquoted(raw)
            if args is not None:
                if separator:
                    yield args
                    args = None
                else:
                    args.append(word)
            if separator or (command_start and raw in KEYWORDS):
                command_start = True
            elif command_start and word == "set" and args is None:
                args, command_start = [], False
            else:
                command_start = False


def turns_on_trace(text):
    if SHEBANG.search(text):
        return True
    for args in set_arguments(text):
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
            'set "-x"',
            "set -o 'xtrace'",
            "if set -x; then :; fi",
            "while set -x; do break; done",
            "until set -x; do :; done",
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
            "# if set -x",
            "echo done # then set -x",
            "printf '%s\\n' 'then set -x for debugging'",
            'echo "if set -x; then"',
            "printf '%s\\n' ';' set -x",
            "find . -exec rm {} \\; set -x",
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

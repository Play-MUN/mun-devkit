# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0

"""No test leaves the gate by a door of its own.

A test that cannot run on a computer is skipped through support.needs() or
support.unavailable(), which say why and, under MDK_REQUIRE_ALL=1 (`make
check-full`), fail instead. A plain unittest skip would pass that gate
silently: this reads the tests' syntax trees and names each one."""

import ast
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAIN = {"skip", "skipIf", "skipUnless", "skipTest", "SkipTest"}
# support.py is where the two ways are written, over unittest's own.
ITS_OWN = {"support.py", Path(__file__).name}


def plain_skips(tree: ast.AST):
    return sorted((node.lineno, node.attr if isinstance(node, ast.Attribute) else node.id)
                  for node in ast.walk(tree)
                  if (isinstance(node, ast.Attribute) and node.attr in PLAIN)
                  or (isinstance(node, ast.Name) and node.id in PLAIN))


class Gate(unittest.TestCase):
    def test_no_test_skips_by_itself(self):
        found = []
        for path in sorted(HERE.glob("*.py")):
            if path.name not in ITS_OWN:
                tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
                found += [f"{path.name}:{line}: {name}" for line, name in plain_skips(tree)]
        self.assertEqual(found, [])

    def test_the_reader_sees_each_kind(self):
        tree = ast.parse("@unittest.skipUnless(x, 'y')\nclass A: pass\n"
                         "def t(self):\n    self.skipTest('z')\n    raise unittest.SkipTest('w')\n"
                         "@needs('reason')\nclass B: pass\n")
        self.assertEqual(plain_skips(tree), [(1, "skipUnless"), (4, "skipTest"), (5, "SkipTest")])


if __name__ == "__main__":
    unittest.main()

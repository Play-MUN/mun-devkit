# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0
"""The licence each file says it is under is the one docs/licensing.md gives
its part of the repository, and the licence texts are in place.

Checked over the files Git tracks; skipped outside a Git checkout."""

import shutil
import subprocess  # nosec B404: asks Git which files it tracks
import unittest

from support import ROOT, isolate_git, needs, unavailable

from mdk import osrepo

COMPILED_IN = {"client/c/mun.c", "client/c/mun.h"}
# Files that cannot carry a comment, or are the terms themselves: they follow
# the table in docs/licensing.md by where they are.
WITHOUT_HEADER = (".md", ".json", ".tscn", ".txt")
WITHOUT_HEADER_NAMES = {".gitignore", "LICENSE", "NOTICE"}


def expected(path: str) -> str:
    if path in COMPILED_IN:
        return "Apache-2.0 WITH LLVM-exception"
    if path.startswith("samples/") or "/addons/" in path:
        return "MIT-0"
    return "Apache-2.0"


def tracked():
    done = subprocess.run(  # nosec B603, B607: no shell, fixed arguments; git from PATH on purpose: the developer's
        ["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True,
        env=osrepo._git_environment())
    return [line for line in done.stdout.splitlines() if line] if done.returncode == 0 else None


GIT = shutil.which("git")


@needs("" if GIT else "git is not installed")
class Licensing(unittest.TestCase):
    def setUp(self):
        isolate_git(self)
        self.tracked = tracked()
        if self.tracked is None:
            unavailable(self, "not a Git checkout")

    def test_every_file_names_the_licence_of_its_part(self):
        wrong = []
        for path in self.tracked:
            file = ROOT / path
            if file.is_symlink() or file.name in WITHOUT_HEADER_NAMES or file.suffix in WITHOUT_HEADER:
                continue
            head = file.read_text(encoding="utf-8").splitlines()[:4]
            named = [line.split("SPDX-License-Identifier:", 1)[1].strip() for line in head
                     if "SPDX-License-Identifier:" in line]
            if named != [expected(path)]:
                wrong.append(f"{path}: says {named or 'nothing'}, its part is {expected(path)}")
            if not any("Copyright 2026 Iván Moreno Mendoza" in line for line in head):
                wrong.append(f"{path}: no copyright line")
        self.assertEqual(wrong, [])

    def test_the_parts_are_the_ones_the_page_names(self):
        page = (ROOT / "docs" / "licensing.md").read_text(encoding="utf-8")
        for words in ("`client/c/mun.h` and `client/c/mun.c`", "`samples/`", "`addons/`", "`mdk new`",
                      "`Apache-2.0`", "`Apache-2.0 WITH LLVM-exception`", "`MIT-0`"):
            self.assertIn(words, page)

    def test_the_licence_texts_are_in_place(self):
        apache = (ROOT / "LICENSES" / "Apache-2.0.txt").read_bytes()
        self.assertEqual((ROOT / "LICENSE").read_bytes(), apache)
        self.assertIn(b"Apache License", apache[:200])
        self.assertIn(b"TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION", apache)
        exception = (ROOT / "LICENSES" / "LLVM-exception.txt").read_text()
        self.assertIn("LLVM Exceptions to the Apache 2.0 License", exception)
        self.assertIn("Sections 4(a), 4(b) and 4(d)", exception)
        mit0 = (ROOT / "LICENSES" / "MIT-0.txt").read_text(encoding="utf-8")
        self.assertTrue(mit0.startswith("MIT No Attribution\n\nCopyright 2026 Iván Moreno Mendoza\n"))
        self.assertNotIn("above copyright notice", mit0)       # the clause MIT has and MIT-0 does not

    def test_a_new_project_s_files_are_the_developer_s_to_use(self):
        from mdk import new
        for item in new.COPIED:
            self.assertEqual(expected(f"samples/hello-mun/{item}"), "MIT-0")


if __name__ == "__main__":
    unittest.main()

# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0

"""The MUN OS revision mdk reports when Git's own variables point elsewhere.

A Git hook exports GIT_DIR, GIT_INDEX_FILE and GIT_WORK_TREE, and whatever it
starts inherits them: `git -C DIR` then still answers for the hook's
repository. Each test runs mdk's reader with those variables naming a decoy
repository, in a temporary folder, and requires the answer to be the
checkout's own and the decoy to be exactly as it was."""

import os
import shutil
import subprocess  # nosec B404: makes Git repositories for the tests
import unittest
from pathlib import Path
from unittest import mock

from support import Scratch, needs

from mdk import osrepo

GIT = shutil.which("git")


def clean_environment():
    local = subprocess.run(  # nosec B603, B607: no shell, fixed arguments; git from PATH on purpose: the developer's
        ["git", "rev-parse", "--local-env-vars"], capture_output=True, text=True).stdout.split()
    return {key: value for key, value in os.environ.items() if key not in local}


def git(directory: Path, *arguments: str) -> str:
    done = subprocess.run(  # nosec B603, B607: no shell, a test's own arguments on a repository it made; git from PATH on purpose: the developer's
        ["git", "-C", str(directory), *arguments], capture_output=True, text=True, check=True,
        env=clean_environment())
    return done.stdout.strip()


def repository(directory: Path, files) -> Path:
    directory.mkdir(parents=True)
    git(directory, "init", "-q", "-b", "main")
    for name, text in files.items():
        (directory / name).parent.mkdir(parents=True, exist_ok=True)
        (directory / name).write_text(text)
    git(directory, "add", "-A")
    git(directory, "commit", "-q", "-m", "first")
    return directory


@needs("" if GIT else "git is not installed")
class InheritedGitVariables(Scratch):
    def setUp(self):
        super().setUp()
        self.checkout = repository(self.scratch / "mun-os", {"tools/mun-card/card.py": "print('card')\n"})
        self.decoy = repository(self.scratch / "decoy", {"kept.txt": "the decoy's file\n"})
        self.before = self.snapshot()
        inherited = {"GIT_DIR": str(self.decoy / ".git"), "GIT_WORK_TREE": str(self.decoy),
                     "GIT_INDEX_FILE": str(self.decoy / ".git" / "index")}
        patch = mock.patch.dict(os.environ, inherited)
        patch.start()
        self.addCleanup(patch.stop)

    def snapshot(self):
        return (git(self.decoy, "rev-parse", "HEAD"), git(self.decoy, "for-each-ref"),
                (self.decoy / ".git" / "config").read_text(), (self.decoy / ".git" / "index").read_bytes(),
                git(self.decoy, "status", "--porcelain"))

    def test_the_revision_read_is_the_checkout_s_not_the_one_the_variables_name(self):
        own = git(self.checkout, "rev-parse", "HEAD")
        self.assertNotEqual(own, self.before[0])
        self.assertEqual(osrepo._git(self.checkout, "rev-parse", "HEAD"), own)
        self.assertEqual(osrepo._git(self.checkout, "rev-parse", "HEAD:tools/mun-card"),
                         git(self.checkout, "rev-parse", "HEAD:tools/mun-card"))
        self.assertEqual(self.snapshot(), self.before, "the decoy changed")

    def test_the_pin_is_compared_with_the_checkout_s_trees_and_changes(self):
        pinned = {"release": "v0.0.0-dev.0", "commit": git(self.checkout, "rev-parse", "HEAD"), "files_sha256": {},
                  "trees": {"tools/mun-card": git(self.checkout, "rev-parse", "HEAD:tools/mun-card")}}
        with mock.patch.object(osrepo, "lock", return_value=pinned):
            self.assertEqual(osrepo.identity(self.checkout)["pin"], "match")
            (self.checkout / "tools/mun-card/card.py").write_text("print('changed')\n")
            found = osrepo.identity(self.checkout)
        self.assertEqual(found["pin"], "differs")
        self.assertEqual(found["differences"], ["tools/mun-card has uncommitted changes"])
        self.assertEqual(self.snapshot(), self.before, "the decoy changed")

    def test_only_the_variables_that_point_git_at_a_repository_are_dropped(self):
        with mock.patch.dict(os.environ, {"MDK_KEPT": "1", "GIT_TERMINAL_PROMPT": "0"}):
            environment = osrepo._git_environment()
        self.assertEqual((environment.get("MDK_KEPT"), environment.get("GIT_TERMINAL_PROMPT")), ("1", "0"))
        for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
            self.assertNotIn(name, environment)


if __name__ == "__main__":
    unittest.main()

# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0

"""`mdk os fetch`: the devkit's own copy of the pinned MUN OS revision is a
clone at exactly the pinned commit, a stale copy is brought to it, and a
repository that does not hold what the lock describes is refused."""

import os
import shutil
import unittest
from unittest import mock

from support import Scratch, needs
from test_osrepo_environment import git, repository

from mdk import osrepo


GIT = shutil.which("git")


@needs("" if GIT else "git is not installed")
class Fetch(Scratch):
    def setUp(self):
        super().setUp()
        self.source = repository(self.scratch / "source", {"tools/mun-card/mun_card/__init__.py": "", "a.txt": "one\n"})
        self.first = git(self.source, "rev-parse", "HEAD")
        (self.source / "a.txt").write_text("two\n")
        (self.source / "tools/mun-card/mun_card/extra.py").write_text("x = 1\n")
        git(self.source, "add", "-A")
        git(self.source, "commit", "-q", "-m", "second")
        self.second = git(self.source, "rev-parse", "HEAD")
        patch = mock.patch.object(osrepo, "FETCHED", self.scratch / "local" / "mun-os")
        patch.start()
        self.addCleanup(patch.stop)

    def pinned(self, commit):
        return {"repository": str(self.source), "release": "v0.0.0-test", "commit": commit, "files_sha256": {},
                "trees": {"tools/mun-card": git(self.source, "rev-parse", f"{commit}:tools/mun-card")}}

    def test_a_clone_at_the_pinned_commit_then_moved_when_the_pin_moves(self):
        with mock.patch.object(osrepo, "lock", return_value=self.pinned(self.first)):
            fetched = osrepo.fetch()
            self.assertEqual(git(fetched, "rev-parse", "HEAD"), self.first)
            self.assertEqual((fetched / "a.txt").read_text(), "one\n")
            self.assertEqual(osrepo.identity(fetched)["pin"], "match")
            with mock.patch.dict(os.environ):
                os.environ.pop("MUN_OS_DIR", None)
                self.assertEqual(osrepo.find(), fetched.resolve())   # found before any ../mun-os
        with mock.patch.object(osrepo, "lock", return_value=self.pinned(self.second)):
            fetched = osrepo.fetch()
            self.assertEqual(git(fetched, "rev-parse", "HEAD"), self.second)
            self.assertTrue((fetched / "tools/mun-card/mun_card/extra.py").is_file())

    def test_a_repository_without_the_pinned_revision_is_refused(self):
        lock = dict(self.pinned(self.first), commit="0" * 40)
        with mock.patch.object(osrepo, "lock", return_value=lock), self.assertRaises(osrepo.MdkError) as raised:
            osrepo.fetch()
        self.assertEqual(raised.exception.code, "E-OS-FETCH")

    def test_a_source_that_looks_like_an_option_is_a_name_not_an_option(self):
        with mock.patch.object(osrepo, "lock", return_value=self.pinned(self.first)):
            osrepo.fetch()                                  # a copy whose remote is a repository on this computer
        (self.source / "a.txt").write_text("three\n")
        git(self.source, "commit", "-q", "-a", "-m", "third")
        third = git(self.source, "rev-parse", "HEAD")       # the copy lacks it: the next fetch asks the remote
        ran = self.scratch / "ran"
        hostile = f"--upload-pack=touch {ran}; git-upload-pack"
        with mock.patch.object(osrepo, "lock", return_value=self.pinned(third)), \
                self.assertRaises(osrepo.MdkError) as raised:
            osrepo.fetch(hostile)
        self.assertEqual(raised.exception.code, "E-OS-FETCH")
        self.assertFalse(ran.exists(), "Git ran a command given as the repository to fetch from")
        # And the same name where there is no copy yet.
        with mock.patch.object(osrepo, "FETCHED", self.scratch / "other" / "mun-os"), \
                mock.patch.object(osrepo, "lock", return_value=self.pinned(third)), \
                self.assertRaises(osrepo.MdkError) as raised:
            osrepo.fetch(hostile)
        self.assertEqual(raised.exception.code, "E-OS-FETCH")
        self.assertFalse(ran.exists())

    def test_a_lock_whose_tree_does_not_match_its_commit_is_refused(self):
        lock = dict(self.pinned(self.first), trees={"tools/mun-card": "0" * 40})
        with mock.patch.object(osrepo, "lock", return_value=lock), self.assertRaises(osrepo.MdkError) as raised:
            osrepo.fetch()
        self.assertEqual(raised.exception.code, "E-OS-PIN")


if __name__ == "__main__":
    unittest.main()

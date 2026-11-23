# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0
"""The tests that use Git are safe to run from a Git hook, and run none of
the developer's Git.

A hook runs with the repository it is committing in the environment (GIT_DIR,
GIT_INDEX_FILE). A test that makes a repository with `git -C DIR init` would
otherwise work on the repository being committed. Here those tests run with
that environment pointing at a separate repository, which must come out
exactly as it was.

Nor may they run what the developer configured for their own work: a hook, a
template's hook, a file-system monitor, a signing program, set globally, in
the XDG configuration or for the whole machine. Here they run under such a
configuration, each program writing its name to a log, and the log must stay
empty.

The same arrangement as MUN OS's tests/test_hook_safety.py.
"""

import os
import shutil
import subprocess  # nosec B404: runs Git, and the tests, under a hostile configuration made here
import sys
import tempfile
import unittest
from pathlib import Path

import gitenv
from support import needs, unavailable

TESTS = Path(__file__).resolve().parent
GIT = shutil.which("git")
# The tests that make repositories or ask Git about one.
USING_GIT = ["test_osrepo_environment", "test_osrepo_fetch", "test_licensing", "test_pack"]


def clean_environment():
    return {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}


def git(repository, environment, *arguments):
    return subprocess.run(  # nosec B603, B607: no shell, a test's own arguments; which git PATH finds is what is under test
        ["git", "-C", str(repository), *arguments], check=True, capture_output=True, text=True,
        env=environment).stdout


def run_the_tests(environment):
    return subprocess.run(  # nosec B603: this Python on this repository's tests, no shell
        [sys.executable, "-m", "unittest", *USING_GIT], cwd=TESTS, env=environment,
        capture_output=True, text=True)


@needs("" if GIT else "git is not installed")
class GitIsolation(unittest.TestCase):
    def test_a_repository_named_by_git_s_variables_is_left_alone(self):
        with tempfile.TemporaryDirectory(prefix="mdk-hook-") as holder:
            sentinel = Path(holder) / "sentinel"
            sentinel.mkdir()
            own = gitenv.environment(Path(holder))
            git(sentinel, own, "init", "-q")
            (sentinel / "kept.txt").write_text("kept\n")
            git(sentinel, own, "add", "kept.txt")
            git(sentinel, own, "commit", "-q", "-m", "sentinel")

            def state():
                hooks = sentinel / ".git" / "hooks"
                return ((sentinel / ".git" / "config").read_text(), git(sentinel, own, "rev-parse", "HEAD"),
                        git(sentinel, own, "for-each-ref"), git(sentinel, own, "ls-files", "--stage"),
                        sorted(path.name for path in hooks.iterdir()) if hooks.is_dir() else [])

            before = state()
            environment = clean_environment()
            environment.update(GIT_DIR=str(sentinel / ".git"), GIT_INDEX_FILE=str(sentinel / ".git" / "index"),
                               GIT_WORK_TREE=str(sentinel))
            done = run_the_tests(environment)
            self.assertEqual(done.returncode, 0, done.stderr[-3000:])
            self.assertEqual(state(), before)

    def test_none_of_the_developer_s_git_runs(self):
        if os.name != "posix":
            unavailable(self, "the hostile programs are POSIX scripts")
        with tempfile.TemporaryDirectory(prefix="mdk-hook-") as holder:
            hostile = Path(holder) / "hostile"
            log = hostile / "ran.log"
            programs, hooks, template = hostile / "bin", hostile / "hooks", hostile / "template" / "hooks"
            for directory in (programs, hooks, template):
                directory.mkdir(parents=True)

            def program(path, status=0):
                path.write_text(f'#!/bin/sh\necho "{path.name} $*" >> "{log}"\nexit {status}\n')
                path.chmod(0o755)

            # The hooks let Git go on, so that every later one is reached; the
            # signing program fails, as a signing key that is not at hand does.
            for name in ("pre-commit", "commit-msg", "post-commit", "post-checkout", "reference-transaction"):
                program(hooks / name)
                program(template / name)
            program(programs / "gpg", status=1)
            program(programs / "fsmonitor")
            configuration = (f'[core]\n\thooksPath = "{hooks}"\n\tfsmonitor = "{programs / "fsmonitor"}"\n'
                             f'[init]\n\ttemplateDir = "{template.parent}"\n'
                             f'[commit]\n\tgpgsign = true\n[tag]\n\tgpgsign = true\n'
                             f'[gpg]\n\tprogram = "{programs / "gpg"}"\n'
                             f'[user]\n\tname = Developer\n\temail = developer@example.invalid\n')
            home = hostile / "home"
            (home / ".config" / "git").mkdir(parents=True)
            (home / ".gitconfig").write_text(configuration)
            (home / ".config" / "git" / "config").write_text(configuration)
            (hostile / "system.gitconfig").write_text(configuration)
            # The machine's configuration too: this `git`, first on PATH, reads
            # the hostile file as its system configuration, set as it starts,
            # where no caller's cleaning of Git's variables reaches it.
            machine = hostile / "machine"
            machine.mkdir()
            (machine / "git").write_text(f'#!/bin/sh\nGIT_CONFIG_SYSTEM="{hostile / "system.gitconfig"}"\n'
                                          f'export GIT_CONFIG_SYSTEM\nexec "{GIT}" "$@"\n')
            (machine / "git").chmod(0o755)
            environment = clean_environment()
            environment.update(HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"),
                               GIT_CONFIG_SYSTEM=str(hostile / "system.gitconfig"),
                               PATH=f"{machine}{os.pathsep}{environment.get('PATH', '')}")
            done = run_the_tests(environment)
            ran = sorted({line.split()[0] for line in log.read_text().splitlines()}) if log.exists() else []
            self.assertEqual(ran, [], "the developer's Git ran in the tests' repositories")
            self.assertEqual(done.returncode, 0, done.stderr[-3000:])


if __name__ == "__main__":
    unittest.main()

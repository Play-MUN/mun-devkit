# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0

"""The hardening of what the devkit compiles for a console, read from what
was built: the properties a program shows (compared with readelf's own
reading), and the options its compile commands carried, for what a program
cannot show.

A program the developer did not compile (an engine's, a library's) is told
what it lacks and not stopped; one the devkit compiles must have all of it.

The tests of built programs are skipped, with the reason, without the SDK
environment or the sample's build (`make sample`)."""

import json
import re
import shutil
import subprocess  # nosec B404: runs make and mdk as a developer would
import sys
import tempfile
import unittest
from pathlib import Path

from support import MUN_OS, ROOT, SAMPLE, Scratch, isolate_git, needs, unavailable

from mdk import checks, container, elf, project
from mdk.errors import MdkError

ENTRY = SAMPLE / "build" / "hello-mun"
COMPILE = ["-fstack-protector-strong", "-fstack-clash-protection", "-D_FORTIFY_SOURCE=3",
           "-mbranch-protection=standard"]
LINK = ["-Wl,-z,relro", "-Wl,-z,now", "-Wl,-z,noexecstack"]
HARDENED = "cc -O2 " + " ".join(COMPILE) + " -fPIE -o build/game game.c -pie " + " ".join(LINK)
PROPERTIES = ["position-independent executable", "full RELRO (GNU_RELRO, BIND_NOW)", "non-executable stack",
              "stack protector (__stack_chk_fail)", "fortified calls", "branch protection (BTI and PAC)"]
# A program that copies into a buffer, so that the stack protector and the
# fortified calls have something to protect.
SOURCE = """#include <stdio.h>
#include <string.h>
int main(int argc, char **argv) {
    char line[64];
    strcpy(line, argc > 1 ? argv[1] : "none");
    printf("%s\\n", line);
    return 0;
}
"""
TOML = """[project]
name = "game"

[card]
id = "org.example.game"
title = "Game"
version = "1.0.0"
profile = "linux-arm64-v0"

[build]
run = "{run}"
entry = "build/game"
{hardening}"""


def codes(findings):
    return [finding.code for finding in findings]


def ready() -> str:
    """"" when programs can be built for a console here, else why not."""
    try:
        if not container.image_exists():
            return "the SDK environment is not built (run `./mdk env build`)"
    except MdkError as exc:
        return exc.message
    return ""


def readelf_properties(directory: Path, relative: str):
    """The same six properties, read by binutils' readelf inside the SDK
    environment: a second reading that shares no code with mdk's."""
    def readelf(*options):
        done = container.run(["readelf", "-W", *options, relative], directory, MUN_OS, capture=True)
        if done.returncode != 0:
            raise AssertionError(f"readelf {options}: {done.stderr}")
        return done.stdout

    header, segments, dynamic = readelf("-h"), readelf("-l"), readelf("-d")
    symbols, notes = readelf("--dyn-syms"), readelf("-n")
    imported = set(re.findall(r"\bUND\s+([^\s@]+)(?:@\S+)?(?:\s+\(\d+\))?\s*$", symbols, re.M))
    stack = re.search(r"GNU_STACK\s+(?:\S+\s+){5}(\S+)", segments)
    flags = " ".join(re.findall(r"\((?:FLAGS|FLAGS_1)\)\s+(?:Flags:\s*)?(.*)", dynamic))
    note = re.search(r"AArch64 feature:\s*(.*)", notes)
    return [
        "DYN" in re.search(r"Type:\s+(\S+)", header).group(1) and "PIE" in flags,
        "GNU_RELRO" in segments and ("BIND_NOW" in flags or re.search(r"\bNOW\b", flags) is not None),
        stack is not None and "E" not in stack.group(1),
        "__stack_chk_fail" in imported,
        any(re.fullmatch(r"__\w+_chk", name) for name in imported),
        note is not None and "BTI" in note.group(1) and "PAC" in note.group(1),
    ]


class BuildCommands(unittest.TestCase):
    """What mdk reads in a build's output."""

    LOG = ("mkdir -p build\n"
           "cc -std=c11 -O2 {compile} -Isrc -c -o build/a.o src/a.c\n"
           "aarch64-linux-gnu-gcc-14 -O2 {compile} -c -o build/b.o 'src/b file.c'\n"
           "cc -o build/game build/a.o build/b.o {link} -lm\n"
           "python3 tools/make_blip.py build/content/sounds/blip.wav\n"
           "make: warning: an unmatched ' quote\n")

    def commands(self, compile_flags=COMPILE, link_flags=LINK):
        return checks.compiler_commands(self.LOG.format(compile=" ".join(compile_flags), link=" ".join(link_flags)))

    def test_the_compiler_s_lines_are_found_and_the_others_left(self):
        found = self.commands()
        self.assertEqual([words[0] for words in found], ["cc", "aarch64-linux-gnu-gcc-14", "cc"])
        self.assertIn("src/b file.c", found[1])
        self.assertEqual(checks.compiler_commands("gcc -E -o /dev/null probe.c\necho cc main.c\n"), [])

    def test_a_line_of_several_commands(self):
        found = checks.compiler_commands("mkdir -p build && cc -O2 -Wl,-z,now -o build/game game.c | tee log; ls\n")
        self.assertEqual(found, [["cc", "-O2", "-Wl,-z,now", "-o", "build/game", "game.c"]])

    def test_complete_commands_leave_no_finding(self):
        self.assertEqual(checks.check_build_commands(self.commands()), [])

    def test_each_missing_option_is_named_with_the_command_that_lacks_it(self):
        for flag in COMPILE:
            findings = checks.check_build_commands(self.commands([f for f in COMPILE if f != flag]))
            self.assertEqual(codes(findings), ["E-HARDEN-BUILD", "E-HARDEN-BUILD"], flag)
            self.assertIn(flag, findings[0].message)
            self.assertIn("src/a.c", findings[0].detail)
        for flag in LINK:
            findings = checks.check_build_commands(self.commands(link_flags=[f for f in LINK if f != flag]))
            self.assertEqual(codes(findings), ["E-HARDEN-BUILD"], flag)
            self.assertIn(flag, findings[0].message)
            self.assertIn("build/a.o", findings[0].detail)

    def test_fortification_is_asked_only_of_an_optimising_command(self):
        without = [flag for flag in COMPILE if not flag.startswith("-D_FORTIFY")]
        for level in ("-O0", ""):
            words = ["cc", *without, "-c", "a.c"] + ([level] if level else [])
            self.assertEqual(checks.check_build_commands([words]), [], level)
        for level in ("-O1", "-O2", "-Os", "-Og", "-O"):
            findings = checks.check_build_commands([["cc", level, *without, "-c", "a.c"]])
            self.assertIn("-D_FORTIFY_SOURCE=3", findings[0].message, level)

    def test_branch_protection_is_an_aarch64_option(self):
        words = ["cc", "-O2", *COMPILE[:3], "-c", "a.c"]
        self.assertEqual(checks.check_build_commands([words], "x86-64"), [])
        self.assertIn("-mbranch-protection=standard", checks.check_build_commands([words], "aarch64")[0].message)


class Probing(Scratch):
    """mk/hardening.mk gives the compiler only the options it accepts."""

    MAKEFILE = ("include {root}/mk/hardening.mk\n"
                "show:\n\t@echo 'C=$(MUN_HARDEN_CFLAGS)'\n\t@echo 'L=$(MUN_HARDEN_LDFLAGS)'\n")

    def setUp(self):
        super().setUp()
        self.compiler = shutil.which("cc")
        if not shutil.which("make") or not self.compiler:
            unavailable(self, "make or a C compiler is missing on this computer")
        (self.scratch / "Makefile").write_text(self.MAKEFILE.format(root=ROOT), encoding="utf-8")

    def flags(self, *settings):
        done = subprocess.run(  # nosec B603, B607: no shell; make from PATH, the developer's, on a makefile the test wrote
            ["make", "-s", "-C", str(self.scratch), "show", *settings], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        fields = dict(line.split("=", 1) for line in done.stdout.splitlines() if "=" in line)
        return fields["C"].split(), fields["L"].split()

    def refusing(self, flag: str) -> str:
        """A compiler that is this computer's, except that it does not know `flag`."""
        wrapper = self.scratch / "cc-without"
        wrapper.write_text(f'#!/bin/sh\nfor a in "$@"; do [ "$a" = "{flag}" ] && '
                           f'{{ echo "unknown option {flag}" >&2; exit 1; }}; done\nexec "{self.compiler}" "$@"\n')
        wrapper.chmod(0o755)
        return str(wrapper)

    def test_an_option_the_compiler_refuses_is_left_out_and_the_others_stay(self):
        compile_flags, link_flags = self.flags("CFLAGS=-O2")
        self.assertIn("-fstack-protector-strong", compile_flags)
        for flag in compile_flags + link_flags:
            if flag.startswith("-D"):
                continue
            left, linked = self.flags("CFLAGS=-O2", "CC=" + self.refusing(flag))
            self.assertEqual(left + linked, [other for other in compile_flags + link_flags if other != flag], flag)

    def test_fortification_follows_optimisation(self):
        self.assertIn("-D_FORTIFY_SOURCE=3", self.flags("CFLAGS=-O2")[0])
        self.assertIn("-D_FORTIFY_SOURCE=3", self.flags("CFLAGS=-g -Os")[0])
        self.assertNotIn("-D_FORTIFY_SOURCE=3", self.flags("CFLAGS=-O0")[0])
        self.assertNotIn("-D_FORTIFY_SOURCE=3", self.flags("CFLAGS=-g")[0])


class ProjectSetting(Scratch):
    def test_hardening_is_required_or_reported_and_nothing_else(self):
        for value, accepted in (('hardening = "required"', True), ('hardening = "report"', True), ("", True),
                                ('hardening = "sometimes"', False), ("hardening = true", False)):
            (self.scratch / project.FILE_NAME).write_text(TOML.format(run="make", hardening=value), encoding="utf-8")
            if accepted:
                project.load(self.scratch, MUN_OS)
            else:
                with self.assertRaises(MdkError, msg=value) as raised:
                    project.load(self.scratch, MUN_OS)
                self.assertEqual(raised.exception.code, "E-PROJECT")


@needs(ready() or ("" if ENTRY.is_file() else f"{ENTRY.relative_to(ROOT)} is not built (run `make sample`)"))
class SampleAsBuilt(unittest.TestCase):
    """The native sample, as `mdk build` left it."""

    def test_the_program_carries_every_property(self):
        found = checks.hardening(elf.read(ENTRY))
        self.assertEqual([label for label, _, _ in found], PROPERTIES)
        self.assertEqual([label for label, ok, _ in found if ok is not True], [])

    def test_readelf_reads_the_same(self):
        self.assertEqual(readelf_properties(SAMPLE, "build/hello-mun"), [True] * 6)

    def test_every_command_of_its_build_carried_every_option(self):
        record = json.loads((SAMPLE / "build" / checks.COMMANDS_FILE).read_text(encoding="utf-8"))
        compiling = [words for words in record["commands"] if any(word.endswith(".c") for word in words)]
        self.assertTrue(compiling)
        for words in compiling:
            for flag in COMPILE + LINK:                    # the sample compiles and links in one command
                self.assertIn(flag, words)
            self.assertIn("/opt/mun-devkit/client/c/mun.c", words)     # the client is built with them too
        self.assertEqual(checks.check_build_commands(record["commands"]), [])

    def test_the_project_requires_it_and_passes_without_a_warning(self):
        found = project.load(SAMPLE, MUN_OS)
        self.assertEqual(found.build.get("hardening"), "required")
        report = checks.check_project(found, MUN_OS)
        self.assertEqual((codes(report["errors"]), codes(report["warnings"])), ([], []), checks.render(report))
        self.assertIn("branch protection: yes", checks.render(report))


@needs(ready())
class Built(unittest.TestCase):
    """Programs built here for a console, with and without the options."""

    def setUp(self):
        isolate_git(self)
        (ROOT / ".local").mkdir(exist_ok=True)              # under the devkit, where the environment can reach it
        self.holder = Path(tempfile.mkdtemp(prefix="harden-", dir=str(ROOT / ".local")))
        self.addCleanup(shutil.rmtree, self.holder, True)

    def mdk(self, *arguments):
        return subprocess.run(  # nosec B603: this Python and this repository's mdk, no shell, with arguments the test wrote
            [sys.executable, str(ROOT / "mdk"), *arguments, "--project", str(self.holder)],
            capture_output=True, text=True, timeout=600)

    def describe(self, run: str, hardening: str = "") -> None:
        (self.holder / "game.c").write_text(SOURCE, encoding="utf-8")
        (self.holder / project.FILE_NAME).write_text(TOML.format(run=run, hardening=hardening), encoding="utf-8")

    def test_a_program_built_without_them_is_told_and_not_stopped(self):
        plain = ("mkdir -p build && cc -O2 -fno-stack-protector -U_FORTIFY_SOURCE -mbranch-protection=none "
                 "-no-pie -o build/game game.c -Wl,-z,norelro -Wl,-z,lazy -Wl,-z,execstack")
        self.describe(plain)
        built = self.mdk("build")
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        self.assertIn("check: passed, 1 warning(s)", built.stdout)
        self.assertIn("W-HARDEN", built.stdout)
        entry = self.holder / "build" / "game"
        self.assertEqual([ok for _, ok, _ in checks.hardening(elf.read(entry))], [False] * 6)
        self.assertEqual(readelf_properties(self.holder, "build/game"), [False] * 6)

        # The same program, in a project that says it compiles it itself.
        self.describe(plain, 'hardening = "required"')
        checked = self.mdk("check", "--json")
        self.assertEqual(checked.returncode, 2, checked.stdout + checked.stderr)
        report = json.loads(checked.stdout)
        self.assertEqual([error["code"] for error in report["errors"]], ["E-HARDEN"] * 6 + ["E-HARDEN-BUILD"])
        self.assertEqual([error["message"].split("lacks: ")[1].rstrip(".") for error in report["errors"][:6]],
                         PROPERTIES)
        for flag in COMPILE + LINK:
            self.assertIn(flag, report["errors"][6]["message"])

    def test_a_program_built_with_them_passes_when_required(self):
        self.describe("mkdir -p build && " + HARDENED, 'hardening = "required"')
        built = self.mdk("build")
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        self.assertIn("check: passed", built.stdout)
        self.assertNotIn("warning", built.stdout)
        self.assertEqual(readelf_properties(self.holder, "build/game"), [True] * 6)

    def test_a_required_program_whose_commands_were_not_seen_is_told_so(self):
        # The properties are in the program; the commands, behind a script that prints nothing.
        (self.holder / "build.sh").write_text("mkdir -p build\n" + HARDENED + "\n", encoding="utf-8")
        self.describe("sh build.sh", 'hardening = "required"')
        built = self.mdk("build")
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        self.assertIn("W-HARDEN-BUILD", built.stdout)
        self.assertNotIn("E-HARDEN", built.stdout)

    def test_in_the_environment_fortification_follows_optimisation(self):
        # The environment's make is not this computer's: the same probes, asked there.
        (self.holder / "Makefile").write_text(Probing.MAKEFILE.format(root="/opt/mun-devkit"), encoding="utf-8")
        for flags, fortified in (("-O2", True), ("-g -Os", True), ("-O0", False), ("-g", False)):
            done = container.run(["make", "-s", "show", f"CFLAGS={flags}"], self.holder, MUN_OS, capture=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            given = done.stdout.splitlines()[0].split("=", 1)[1].split()
            self.assertEqual("-D_FORTIFY_SOURCE=3" in given, fortified, flags)
            for flag in COMPILE[:2] + COMPILE[3:]:
                self.assertIn(flag, given)

    def test_the_client_builds_clean_with_them_and_carries_them(self):
        done = container.run(["make", "-f", "/opt/mun-devkit/client/c/Makefile", "BUILD=/work/build"],
                             self.holder, MUN_OS, capture=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        for flag in COMPILE + LINK:
            self.assertIn(flag, done.stdout.split())
        self.assertEqual([label for label, ok, _ in checks.hardening(elf.read(self.holder / "build" / "munc"))
                          if ok is not True], [])
        self.assertEqual(readelf_properties(self.holder, "build/munc"), [True] * 6)
        ran = container.run(["build/munc", "facts"], self.holder, MUN_OS, capture=True,
                            env={"MUN_SESSION": "s1", "MUN_CARD_ID": "mun.test"})
        self.assertEqual(ran.returncode, 0, ran.stderr)
        self.assertIn("card_id=mun.test", ran.stdout)


if __name__ == "__main__":
    unittest.main()

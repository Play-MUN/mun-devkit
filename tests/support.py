# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0

"""Shared by the tests: the devkit's paths, the MUN OS checkout, and a way to
talk to a save socket as a game would."""

import json
import os
import shutil
import socket
import subprocess  # nosec B404: the tests compile the client's test program and run it
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "mdk"))

import gitenv  # these two after the path above, on purpose
from mdk import osrepo, sim

# How long a test waits for something that must happen before it gives up
# and fails. It bounds a failure and never decides a result: no test passes
# because this much time went by.
PATIENCE = 60.0

MUN_OS = osrepo.find()
SAVES = osrepo.mun_card(MUN_OS).saves
SAMPLE = ROOT / "samples" / "hello-mun"


def isolate_git(test: unittest.TestCase) -> None:
    """Give `test` Git of its own (tests/gitenv.py) until it ends: every git
    it starts, and every git the code it runs starts, sees neither the
    developer's configuration nor a hook's variables."""
    holder = Path(tempfile.mkdtemp(prefix="mdk-git-", dir="/tmp"))  # nosec B108: a private mkdtemp directory; /tmp keeps the paths short
    test.addCleanup(shutil.rmtree, holder, True)
    gitenv.isolate(test, holder)


def unavailable(test: unittest.TestCase, reason: str) -> None:
    """End `test` because it cannot run here: skipped, or failed under
    MDK_REQUIRE_ALL=1 (`make check-full`)."""
    if os.environ.get("MDK_REQUIRE_ALL") == "1":
        test.fail(f"required, and not possible here: {reason}")
    test.skipTest(reason)


def needs(reason: str):
    """For a test class that needs something this computer may lack (the SDK
    environment, the sample's build, the engine): `reason` is why it cannot
    run, or "" when it can. The class is then skipped with that reason; with
    MDK_REQUIRE_ALL=1 (`make check-full`) it fails instead, so that a check
    used as a gate cannot pass by not running."""
    def wrap(cls):
        if not reason:
            return cls
        if os.environ.get("MDK_REQUIRE_ALL") == "1":
            def refuse(klass):
                raise AssertionError(f"required, and not possible here: {reason}")
            cls.setUpClass = classmethod(refuse)
            return cls
        return unittest.skip(reason)(cls)
    return wrap


class Scratch(unittest.TestCase):
    """A test with a short scratch directory (a UNIX socket's path is limited)."""

    def setUp(self):
        self.scratch = Path(tempfile.mkdtemp(prefix="mdk-", dir="/tmp"))  # nosec B108: a private mkdtemp directory; /tmp keeps a socket's path short
        self.addCleanup(shutil.rmtree, self.scratch, True)
        isolate_git(self)

    def card(self, card_id="mun.test", version="1.0.0"):
        return sim.SimCard(self.scratch / "card", card_id, version, SAVES)

    def gate(self, card=None, **options):
        gate = sim.SaveGate(self.scratch / "save.sock", card or self.card(), "stest", **options)
        self.addCleanup(gate.close)
        return gate


def ask(path, data: bytes, timeout: float = PATIENCE, half_close: bool = False):
    """Send `data` to the socket and return what comes back: the decoded
    answer line, or "" when the peer closed without one. (None if nothing
    came within `timeout`: a test that expects silence uses attended().)"""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(timeout)
        connection.connect(str(path))
        try:
            connection.sendall(data)
        except OSError:
            pass                        # the peer may close while a long line is still being sent
        if half_close:
            connection.shutdown(socket.SHUT_WR)
        received = b""
        try:
            while b"\n" not in received:
                chunk = connection.recv(65536)
                if not chunk:
                    return json.loads(received) if received.strip() else ""
                received += chunk
        except socket.timeout:
            return None
        except OSError:
            return ""
        return json.loads(received.split(b"\n", 1)[0])


def attended(gate, connection: socket.socket):
    """What the service has done with what `connection` sent, once it is
    known to have dealt with it: None when it has not answered and holds the
    connection open, "" when it closed it, else its decoded answer.

    The service reads its connections in one thread, and a connection made
    later is read later: when it has answered a request made after this one,
    it has read this one. The request used is refused as invalid, so it
    leaves the card as it was and one "save_invalid" in the gate's record."""
    marker = ask(gate.path, save_line({}, schema=0))
    if not marker or marker.get("error", {}).get("code") != "save_invalid":
        raise AssertionError(f"the service did not attend the marker request: {marker!r}")
    connection.setblocking(False)
    try:
        received = connection.recv(65536)
    except BlockingIOError:
        return None
    finally:
        connection.setblocking(True)
    return json.loads(received.split(b"\n", 1)[0]) if received.strip() else ""


def connect(test: unittest.TestCase, path) -> socket.socket:
    """A connection to the socket at `path`, closed when the test ends."""
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    test.addCleanup(connection.close)
    connection.settimeout(PATIENCE)
    connection.connect(str(path))
    return connection


def save_line(data, schema=1, kind="save") -> bytes:
    return (json.dumps({"type": kind, "schema": schema, "data": data}) + "\n").encode("utf-8")


def compile_munc(directory: Path) -> Path:
    """The client's test program, built for this computer, with the sanitizers
    the compiler offers."""
    compiler = shutil.which("cc")
    if not compiler:
        if os.environ.get("MDK_REQUIRE_ALL") == "1":
            raise AssertionError("required, and not possible here: no C compiler on this computer")
        raise unittest.SkipTest("no C compiler on this computer")
    target = directory / "munc"
    sources = [str(ROOT / "client" / "c" / "tests" / "munc.c"), str(ROOT / "client" / "c" / "mun.c")]
    common = [compiler, "-std=c11", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-g", f"-I{ROOT / 'client' / 'c'}"]
    for extra in (["-fsanitize=address,undefined", "-fno-sanitize-recover=all"], []):
        done = subprocess.run(  # nosec B603: this computer's compiler by the full path which() found, no shell, on the devkit's own sources
            common + extra + ["-o", str(target)] + sources, capture_output=True, text=True)
        if done.returncode == 0:
            return target
    raise AssertionError("the client does not compile:\n" + done.stderr)


def munc(program: Path, arguments, environment=None, stdin: bytes = b"", timeout: float = 20.0) -> dict:
    """Run munc and return its "name=value" lines as a dictionary."""
    env = {"PATH": os.environ.get("PATH", ""), **(environment or {})}
    done = subprocess.run(  # nosec B603: the program the tests just compiled, with a test's own arguments and no shell
        [str(program), *arguments], input=stdin, capture_output=True, env=env, timeout=timeout)
    if done.returncode not in (0, 2) or done.stderr:
        raise AssertionError(f"munc {arguments} ended with {done.returncode}:\n{done.stderr.decode('utf-8', 'replace')}")
    fields = {}
    for line in done.stdout.decode("utf-8").splitlines():
        name, _, value = line.partition("=")
        fields[name] = value
    return fields

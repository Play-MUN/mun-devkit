# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0

"""What mdk can tell about a build before a card is made of it.

Each finding has a stable code, a sentence and a next step. Errors are things
the console is known to refuse or the game cannot work with; warnings are
things worth a look. None of this replaces the console: the card tool
validates the card, and a console runs the game."""

import hashlib
import json
import re
import shlex
from pathlib import Path
from typing import Any, Dict, List, Tuple

from . import elf, osrepo
from .errors import MdkError
from .project import Project

MIB = 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _version_tuple(text: str) -> Tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def check_entry(path: Path, profile: Dict[str, Any]) -> Tuple[List[MdkError], List[MdkError], Dict[str, Any]]:
    """The entry against the runtime profile: errors, warnings and the facts read."""
    errors: List[MdkError] = []
    warnings: List[MdkError] = []
    name = path.name
    if not path.is_file():
        return [MdkError("E-ENTRY", f"The entry {path} does not exist.", "Build the project first (`mdk build`).")], [], {}
    if not elf.is_elf(path):
        return [MdkError("E-NOT-ELF", f"{name} is not an ELF program.",
                         "The entry must be the game's executable, built for AArch64 Linux; "
                         "a script or a Windows or macOS program cannot be one.")], [], {}
    try:
        info = elf.read(path)
    except elf.NotElf as exc:
        return [MdkError("E-NOT-ELF", f"{name} is a damaged ELF file: {exc}.", "Rebuild it.")], [], {}
    facts = {"file": str(path), "sha256": sha256_file(path), **info}
    if info["bits"] != 64 or info["endian"] != "little" or info["machine"] != profile["machine"]:
        errors.append(MdkError(
            "E-ARCH", f"{name} is a {info['bits']}-bit {info['endian']}-endian {info['machine']} program. "
            "MUN runs 64-bit AArch64 Linux programs.",
            "Build or export it for Linux ARM64 (aarch64); a Windows, macOS or x86-64 build must be made again."))
        return errors, warnings, facts
    if "executable" not in info["type"]:
        errors.append(MdkError("E-NOT-PROGRAM", f"{name} is a {info['type']} file, not a program.",
                               "Name the linked executable as the entry."))
    limit = profile["entry_max_bytes"]
    if info["size"] > limit:
        errors.append(MdkError(
            "E-SIZE", f"{name} is {info['size'] / MIB:.1f} MiB; the console copies an entry of at most "
            f"{limit // MIB} MiB into memory.",
            "Strip debugging symbols, build with size options, or move data out of the executable into the content."))
    if not info["static"]:
        if info["interpreter"] != profile["interpreter"]:
            errors.append(MdkError(
                "E-INTERP", f"{name} asks for the loader {info['interpreter']}; the console has {profile['interpreter']}.",
                "Build with the SDK environment (`mdk build`) rather than another toolchain."))
        allowed = set(profile["base_libraries"]) | set(profile["libraries"])
        for library in info["needed"]:
            if library not in allowed:
                provided = ", ".join(sorted(profile["libraries"])) or "none beyond the C library"
                errors.append(MdkError(
                    "E-LIB", f"{name} needs {library}, which the profile {profile['profile']} does not provide.",
                    "Link it into the game statically, or drop the feature that uses it. The card's content is "
                    "read-only data: a library placed there cannot be loaded.",
                    f"The profile provides: {provided}."))
        if info["runpath"]:
            warnings.append(MdkError(
                "W-RUNPATH", f"{name} has a library search path ({':'.join(info['runpath'])}).",
                "Only the entry is copied to where it runs: nothing will be beside it. Libraries must be the "
                "console's own or linked in."))
        if info["glibc"] and _version_tuple(info["glibc"]) > _version_tuple(profile["glibc"]):
            errors.append(MdkError(
                "E-GLIBC", f"{name} needs glibc {info['glibc']}; the console has {profile['glibc']}.",
                "Build inside the SDK environment (`mdk build`), which has the console's own versions, "
                "instead of on the host."))
    return errors, warnings, facts


def hardening(info: Dict[str, Any]) -> List[Tuple[str, Any, str]]:
    """What a program's hardening can be read from the file itself:
    (property, True / False / None when the file cannot say, detail).

    A statically linked program imports nothing, so its stack protector and
    fortified calls cannot be seen; and nothing in a program shows whether it
    was built with stack-clash protection: that is in the build's commands."""
    fortified = [name for name in info.get("imports", [])
                 if name.startswith("__") and name.endswith("_chk")]
    seen = None if info.get("static") else True
    marks = info.get("branch_protection", [])
    return [
        ("position-independent executable", bool(info.get("pie")), ""),
        ("full RELRO (GNU_RELRO, BIND_NOW)", bool(info.get("relro") and info.get("bind_now")), ""),
        ("non-executable stack", info.get("nx_stack") if info.get("nx_stack") is not None else False, ""),
        ("stack protector (__stack_chk_fail)", seen and "__stack_chk_fail" in info.get("imports", []), ""),
        ("fortified calls", seen and bool(fortified), ", ".join(fortified[:4])),
        ("branch protection (BTI and PAC)", {"BTI", "PAC"} <= set(marks) if info.get("machine") == "aarch64" else None,
         "note: " + (" ".join(marks) or "none")),
    ]


def check_hardening(name: str, info: Dict[str, Any], required: bool) -> List[MdkError]:
    """Findings for the properties the program lacks: errors when the project
    requires them (what the devkit itself compiles), one warning otherwise.
    An engine's or a library's objects are not the developer's to rebuild:
    for them mdk says what it sees and goes on."""
    missing = [label for label, ok, _ in hardening(info) if ok is False]
    if not missing:
        return []
    remedy = "Build with the devkit's options (`include $(MUN_DEVKIT)/mk/hardening.mk`)."
    marking = (" The linker marks a program for BTI and PAC only when every object in it is marked: an "
               "engine's or a library's own objects may not be yours to change.")
    if required:
        return [MdkError("E-HARDEN", f"{name} lacks: {label}.", remedy + (marking if "BTI" in label else ""))
                for label in missing]
    return [MdkError("W-HARDEN", f"{name} lacks: {'; '.join(missing)}.",
                     remedy + (marking if any("BTI" in label for label in missing) else "")
                     + "\nReported, not required: set build.hardening = \"required\" in "
                     "mun-project.toml for a program you compile yourself.")]


COMMANDS_FILE = "compile-commands.json"
COMPILER = re.compile(r"(?:[\w.+]+-)*(?:cc|gcc|g\+\+|c\+\+|clang|clang\+\+)(?:-[\d.]+)?")
SOURCES = (".c", ".cc", ".cpp", ".cxx", ".C", ".m", ".mm")
COMPILE_FLAGS = ("-fstack-protector-strong", "-fstack-clash-protection")
LINK_FLAGS = ("-Wl,-z,relro", "-Wl,-z,now", "-Wl,-z,noexecstack")


def compiler_commands(log: str) -> List[List[str]]:
    """The compiler's commands in a build's output, as arguments: the lines
    a build tool echoes before running them (make does; a tool that prints
    none leaves nothing to read). A line may hold several commands
    (`mkdir -p build && cc ...`)."""
    found = []
    for line in log.splitlines():
        lexer = shlex.shlex(line, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        try:
            tokens = list(lexer)
        except ValueError:                # not a command line: an unmatched quote
            continue
        words: List[str] = []
        for token in tokens + [";"]:
            if token and not set(token) - set("();<>|&"):          # an operator: the command ends here
                if words and words[-1].isdigit() and token[0] in "<>":
                    words.pop()               # the 2 of `2>&1` belongs to the redirection
                if words and COMPILER.fullmatch(Path(words[0]).name) and not {"-E", "-M", "-MM"} & set(words):
                    found.append(words)
                words = []
            else:
                words.append(token)
    return found


def check_build_commands(commands: List[List[str]], machine: str = "aarch64") -> List[MdkError]:
    """What a program does not show: that every object was compiled with the
    stack protector (the program shows only that some function has one),
    with stack-clash protection (no mark at all) and fortified (only the
    calls that could be show); and that it was linked with the three -z
    options. One finding per command that lacks an option."""
    findings = []
    for words in commands:
        compiles = any(word.endswith(SOURCES) for word in words if not word.startswith("-"))
        links = not {"-c", "-S"} & set(words)
        wanted: List[str] = []
        if compiles:
            wanted += COMPILE_FLAGS
            levels = [word for word in words if re.fullmatch(r"-O\w*", word)]
            if levels and levels[-1] != "-O0":           # the C library refuses to fortify an unoptimised build
                wanted.append("-D_FORTIFY_SOURCE=3")
            if machine == "aarch64":
                wanted.append("-mbranch-protection=standard")
        if links:
            wanted += LINK_FLAGS
        lacking = [flag for flag in wanted if flag not in words]
        if lacking:
            inputs = [word for word in words if not word.startswith("-") and word.endswith(SOURCES + (".o",))]
            findings.append(MdkError(
                "E-HARDEN-BUILD", f"A build command lacks {' '.join(lacking)}.",
                "Give every compile and link command the devkit's options: $(MUN_HARDEN_CFLAGS) and "
                "$(MUN_HARDEN_LDFLAGS) from mk/hardening.mk.",
                " ".join(inputs[:6]) or " ".join(words[:6])))
    return findings


def check_content(directory: Path, entry_name: str) -> Tuple[List[MdkError], List[MdkError], Dict[str, Any]]:
    """The data tree that will be the card's content."""
    errors: List[MdkError] = []
    warnings: List[MdkError] = []
    if not directory.is_dir():
        return [MdkError("E-CONTENT", f"The content directory {directory} does not exist.",
                         "Build the project first, or remove build.content from mun-project.toml.")], [], {}
    files = total = 0
    for path in sorted(directory.rglob("*")):
        relative = path.relative_to(directory)
        if path.is_symlink():
            errors.append(MdkError("E-CONTENT-LINK", f"content/{relative} is a symbolic link.",
                                   "A card holds files and folders only; copy the file itself."))
            continue
        if not path.is_file():
            continue
        files += 1
        total += path.stat().st_size
        if elf.is_elf(path):
            warnings.append(MdkError(
                "W-CODE", f"content/{relative} is program code inside the content.",
                "The console mounts the content read-only and not executable: this file can be read as data "
                "but never run or loaded as a library. Link what the game needs into the entry."))
    if (directory / entry_name).exists():
        errors.append(MdkError("E-CONTENT-ENTRY", f"The content already has something named {entry_name}, "
                               "the name the entry takes on the card.", "Rename or exclude it."))
    return errors, warnings, {"files": files, "bytes": total}


def check_project(project: Project, mun_os: Path) -> Dict[str, Any]:
    """Everything mdk checks for a project. Returns a report:
    {"ok", "errors", "warnings", "entry", "content", "card"}."""
    validate = osrepo.mun_card(mun_os).validate
    errors: List[MdkError] = []
    warnings: List[MdkError] = []
    card = project.card
    if not validate.ID_PATTERN.fullmatch(card["id"]):
        errors.append(MdkError("E-CARD-ID", f"card.id {card['id']!r} is not valid.",
                               "3 to 64 characters: lowercase letters, digits, '.', '-' or '_', starting with a "
                               "letter or digit. Keep one id for every edition of the same game: it names the save."))
    if not validate.VERSION_PATTERN.fullmatch(card["version"]):
        errors.append(MdkError("E-CARD-VERSION", f"card.version {card['version']!r} is not valid.",
                               "Use up to four dot-separated numbers, for example 1.2.0."))
    if not card["title"].strip() or len(card["title"]) > validate.TITLE_MAX_CHARS:
        errors.append(MdkError("E-CARD-TITLE", "card.title is empty or longer than "
                               f"{validate.TITLE_MAX_CHARS} characters."))
    if card["profile"] not in validate.PROFILES:
        errors.append(MdkError("E-PROFILE", f"This MUN OS revision's validator does not know the profile "
                               f"{card['profile']!r}.", "It knows: " + ", ".join(validate.PROFILES) + "."))
    entry_errors, entry_warnings, entry = check_entry(project.entry, project.profile)
    errors += entry_errors
    warnings += entry_warnings
    if entry and not entry_errors:
        required = project.build.get("hardening") == "required"
        (errors if required else warnings).extend(check_hardening(project.entry.name, entry, required))
        if required:
            try:
                record = json.loads((project.output / COMMANDS_FILE).read_text(encoding="utf-8"))
                commands = [words for words in record["commands"] if isinstance(words, list)]
            except (OSError, ValueError, KeyError, TypeError):
                commands = []
            if commands:
                errors += check_build_commands(commands, entry.get("machine", ""))
            else:
                warnings.append(MdkError(
                    "W-HARDEN-BUILD", "The build's compile commands were not seen.",
                    "Stack-clash protection leaves no mark in a program: mdk reads it from the commands "
                    "`mdk build` saw the build print. Build with `mdk build`, with a tool that prints them."))
    content: Dict[str, Any] = {}
    if project.content is not None:
        if project.profile["card_variant"] != "game-gl":
            errors.append(MdkError("E-CONTENT", f"The card tool adds content only to a {project.profile['profile']} "
                                   "card's GL variant.", "Use the GL profile, or keep the data inside the entry."))
        content_errors, content_warnings, content = check_content(project.content, project.entry.name)
        errors += content_errors
        warnings += content_warnings
    size_mib = card.get("size_mib")
    if entry and isinstance(size_mib, int):
        need = entry.get("size", 0) + content.get("bytes", 0)
        # The file system's own structures and room for saves: a rough margin,
        # stated as such. The card tool has the last word.
        if need + 6 * MIB > size_mib * MIB:
            warnings.append(MdkError(
                "W-CARD-SIZE", f"The entry and content take {need / MIB:.1f} MiB of a {size_mib} MiB card.",
                "Leave room for the file system and the saves: raise card.size_mib."))
    return {"ok": not errors, "errors": errors, "warnings": warnings, "entry": entry, "content": content, "card": card}


def render(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    entry = report.get("entry") or {}
    if entry:
        linkage = "static" if entry.get("static") else "needs " + (", ".join(entry.get("needed", [])) or "nothing")
        lines.append(f"entry    {Path(entry['file']).name}: {entry['size'] / MIB:.2f} MiB, {entry['machine']}, {linkage}"
                     + (f", glibc {entry['glibc']}" if entry.get("glibc") else ""))
        lines.append(f"         sha256 {entry['sha256']}")
        if entry.get("machine") == "aarch64" and "pie" in entry:
            words = {True: "yes", False: "NO", None: "cannot tell"}
            said = [f"{label.split(' (')[0]}: {words[ok]}" for label, ok, _ in hardening(entry)]
            lines.append("hardening " + "; ".join(said[:3]) + ";")
            lines.append("          " + "; ".join(said[3:]))
    content = report.get("content") or {}
    if content:
        lines.append(f"content  {content['files']} files, {content['bytes'] / MIB:.2f} MiB")
    for finding in report["warnings"] + report["errors"]:
        lines.append(finding.render())
    lines.append("check: " + ("passed" if report["ok"] else f"{len(report['errors'])} error(s)")
                 + (f", {len(report['warnings'])} warning(s)" if report["warnings"] else ""))
    return "\n".join(lines)

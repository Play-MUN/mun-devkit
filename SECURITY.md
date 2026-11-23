# Security

**English** · [Español](SECURITY.es.md)

MUN™ Devkit is early: tools, a client and samples for a console that is
still in development, with no release of its own yet. It reads files it
did not write and puts code into other people's games, so it has boundaries
that are meant to hold, and reports about them are welcome.

## Reporting a vulnerability

Report it privately, not in a public issue:

- on GitHub, **Security → Report a vulnerability** in this repository, or
- by e-mail to **hello@playmun.com**, with "security" in the subject.

Say what is affected (the commit, and what `./mdk doctor` prints), how to
reproduce it, and what it lets someone do. One person maintains the devkit:
expect an answer within a few days, not hours, and to be kept informed
after it. A fix lands on `dev`, then on `main`, and is published as a
security advisory of this repository. Please give that time before telling
anyone else, and say whether you want to be credited.

## What is in scope

What the devkit promises to protect:

- **Files as untrusted input.** What `mdk check`, `mdk pack` and `mdk sim`
  read: the program a project names as its entry (`tools/mdk/mdk/elf.py`),
  `mun-project.toml`, a content directory, a save file, a build's output.
  A file that makes a tool crash, hang, write outside the project or run
  something is a finding.
- **The client inside a game** (`client/c`, `engines/godot/addons/mun`): the
  save file and the console's answers it reads, and the memory it touches.
  A game compiles this code in, so a fault here is a fault in every game.
- **What the devkit downloads and trusts**: the pinned MUN OS revision
  (`mun-os.lock.json`, `mdk os fetch`), the build environment's base image
  and package snapshot (`tools/env/Dockerfile`), the pinned engine
  (`engines/godot/fetch.sh`) and the analysers
  (`tools/dev-requirements.txt`). A way to make any of them accept
  something other than what is pinned is a finding.
- **The checks' word.** A program that `mdk check` reports as hardened, or
  as fit for its runtime profile, and is not.

## What is out of scope

- **The session simulator is not a sandbox.** `mdk sim` runs the game with
  the developer's own rights, on purpose: it reproduces a session's
  contracts, not the console's confinement.
- **A project's own build.** `mdk build` runs the build command the project
  names, inside the build environment. What that command does there is the
  project's, as with any source tree you choose to build; the container
  runtime's and the host computer's own security are theirs.
- **MUN OS**: the card format and its validator, the card service, the
  launcher and the game's sandbox. Its own
  [security page](https://github.com/Play-MUN/mun-os/blob/main/SECURITY.md)
  says how to report those.
- **A game made with the devkit**: its faults are its author's to hear
  about.

## Supported versions

Only `main` and `dev`. There is no release yet; when there is one, only the
latest gets fixes.

# Licensing

MUN Devkit's own work is Copyright 2026 Iván Moreno Mendoza, who develops
MUN™ as Play MUN. It is licensed in three parts, by where each part ends up.

| Part | Where it ends up | Licence |
| --- | --- | --- |
| The tools: `mdk`, the session simulator, the build environment, the tests, `contracts/`, the documentation. Everything not named in the next two rows | On the developer's computer | [Apache License 2.0](../LICENSE) (`Apache-2.0`) |
| The client a game compiles in: `client/c/mun.h` and `client/c/mun.c` | Inside the game, compiled | Apache License 2.0 with the LLVM Exceptions (`Apache-2.0 WITH LLVM-exception`): [the licence](../LICENSES/Apache-2.0.txt) and [the exception](../LICENSES/LLVM-exception.txt) |
| What a developer copies and makes their own: `samples/`, an engine's `addons/`, and everything `mdk new` puts in a new project | In the game's own source | [MIT No Attribution](../LICENSES/MIT-0.txt) (`MIT-0`) |

Every file that can carry a comment names its licence in its first lines
(`SPDX-License-Identifier`). A file that cannot (JSON, a scene, a page of
documentation) follows the table by where it is. `tests/test_licensing.py`
checks both.

## What that means for a game

- **The compiled client asks nothing of the game.** The Apache License asks
  whoever redistributes a work to carry the licence and its notices. The
  exception lifts that for the client as it is compiled into a game: the
  game ships without them. A copy of the client's source keeps its header.
- **Samples, the starter project and the engine add-ons are yours to use
  as you like**: change them, ship them, sell what you make with them, with
  no attribution and nothing to include.
- **The tools** may be used, changed and redistributed under the Apache
  License; using them puts no condition on what you make with them.
- The Apache License also grants a patent licence from each contributor,
  and ends it for whoever sues over the work.
- A game stays its author's. Nothing here asks for its source, a fee, an
  account or an agreement.

All of it comes without warranty, as each licence says.

## Making a game and publishing it on a MUN Disk are two things

- **The devkit is free.** Anyone may make, test and distribute their games
  with it, at no charge.
- **An official MUN Disk is a service.** Its signing, its manufacture and
  its physical edition go with a publishing agreement of their own with
  Play MUN. These licences neither grant that nor say what its terms are.

The MUN and Play MUN names and logos are not licensed by any of the three
licences; their terms are in [NAME-AND-LOGO.txt](../NAME-AND-LOGO.txt).

## Contributions

Contributions stay their authors'. What you intentionally submit for
inclusion is under the licence of the part it goes into, with no additional
conditions (section 5 of the Apache License; the same holds here for the
`MIT-0` part). The `Signed-off-by:` line that `git commit -s` adds certifies
the [Developer Certificate of Origin 1.1](https://developercertificate.org/):
that you wrote the change or otherwise have the right to submit it under
that licence.

## Third-party material

One text in this repository comes from elsewhere: the
[code of conduct](../CODE_OF_CONDUCT.md) and its Spanish translation are the
Contributor Covenant 2.1, under the Creative Commons Attribution 4.0
International licence, with its attribution in the text. Nothing else is
copied in. [What the devkit uses](third-party.md), and under which terms, is
listed apart. A
game made with an engine carries that engine's own notices: the engine's
licence is not the devkit's to give.

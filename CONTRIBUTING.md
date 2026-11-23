# Contributing

**English** · [Español](CONTRIBUTING.es.md)

MUN™ Devkit is at an early stage: it builds, checks, packs and simulates a
game for a console that is still in development, and nothing in it has run
on that console's hardware. Contributions are welcome: fixes, tests,
documentation, samples, engine adapters. Read the [README](README.md)
first; it says what exists and what does not.

Everyone taking part follows the [code of conduct](CODE_OF_CONDUCT.md).

## Ways to help

Not all help is code. Each of these goes through an issue or a pull request
against `dev`, as the rest of this page describes:

- **Try it on your computer.** Follow the README from `./mdk doctor` to a
  saved game on Linux x86-64, on a Mac with an Intel processor, or on a
  Linux distribution other than Ubuntu. Report what happened with the bug report template; a report
  that it works counts as much as one that it does not.
- **Bring a game to a card.** Take an SDL2 or OpenGL game you may
  redistribute through `mdk new`, `build`, `check`, `pack` and `sim`, and
  turn every step you had to guess into a fix.
- **Errors and unclear instructions.** A step that does not do what the
  page says is a bug in the documentation: open an issue, or a pull request
  that fixes the page, in English and, when it has one, in its translation.
- **Translations.** The Spanish pages are kept against their English
  originals ([below](#documentation-and-translations)). A new language
  starts as a proposal in an issue.
- **An engine.** An adapter or a recipe for an engine that can produce a
  Linux ARM64 game: propose it in an issue first, with what the engine
  needs from a session.

Questions go in an issue or in the developers' channel of the
[MUN Discord](https://discord.gg/UxgExjjhxH). Decisions are recorded in issues, so that whoever comes
later can find them.

## Your first contribution

The rest of this page says what a change to the client or to a contract
must come with. A first contribution needs much less:

1. Pick an issue labelled
   [good first issue](https://github.com/Play-MUN/mun-devkit/labels/good%20first%20issue),
   or fix something small you ran into: a typo, a step that was not clear,
   an error message that did not help.
2. Fork the repository, make a branch from `dev`, change it, and run
   `make check`.
3. Commit with `git commit -s`. The `-s` adds a line saying the change is
   yours to give ([below](#rights-and-sign-off)); that is all there is to
   it.
4. Open a pull request against `dev` and say what you ran.

If the change needs a test and you are not sure how to write it, or it
touches a page that has a translation and you do not write Spanish, say so
in the pull request: the maintainer adds what is missing or shows you how.
Nobody is expected to know this page by heart the first time.

## Who decides

MUN Devkit is founded and maintained by Iván Moreno Mendoza (Play MUN).
The maintainer reviews pull requests and decides what goes into `dev` and,
from it, into `main`. He is one person and answers when he can. A fork may
of course go its own way ([NAME-AND-LOGO.txt](NAME-AND-LOGO.txt) says how
it may name itself).

## Before you start

- **Small fixes and documentation**: open a pull request directly.
- **Anything larger** (a new command, a new dependency, an engine, a change
  a game can see): open an issue first and describe the problem and the
  proposal, so it can be discussed before you spend time on it.
- **A change to `client/` or `contracts/` reaches every game.** It is
  agreed in an issue before it is written, and it says what a game built
  against the earlier contract meets. The card format, its validator and
  the save rules are MUN OS's: a change to those belongs
  [there](https://github.com/Play-MUN/mun-os).
- Security problems go privately to the maintainer, not to an issue
  ([security](SECURITY.md)).

## Set up and checks

The README's *What you need* lists the requirements. Then:

```sh
./mdk doctor        # what this computer has and lacks
./mdk os fetch      # MUN OS's tools at the pinned revision
make check          # the tests this computer can run; it names the ones it skipped
```

`make check` needs Python 3.9 or later and Make; a C compiler adds the
client's tests. The tests that build or run a console program need a
container runtime and more:

```sh
./mdk env build             # the build environment (needs the network once)
make sample                 # the native sample, built and packed
engines/godot/fetch.sh      # the pinned engine, for the adapter's tests
make dev-tools              # the pinned analysers, into .local/venv
make check-full             # every test; one that cannot run fails
make analyse                # pyflakes and bandit
```

Pull requests run `make check` on Linux and macOS and `make check-full` on
Linux ARM64. Say in the pull request which checks you ran and which you
could not: a skipped test is not a passed one.

## Changes

- Keep a change to one purpose.
- **A fix or a new behaviour comes with a test that fails before it and
  passes after it.** Say so in the pull request.
- **Tests wait for what happened, not for time.** No sleep, and no timeout
  that decides a result: wait for the state (a save is in the card, a
  process has ended). `tests/test_no_clock.py` checks it.
- **An analyser's warning is fixed, or reviewed on its own line**: the rule
  and the reason, `# nosec B603: no shell; ...`. Never for a file or a rule
  as a whole. `tests/test_static.py` holds every mark to a warning.
- Treat every file the tools read as untrusted input: bounds before use,
  and an error with a code, what is wrong and what to do.
- `mdk` uses Python's standard library only. A new dependency is proposed
  in an issue.
- The C client creates no thread, keeps no global state and allocates only
  the session; `client/c/mun.h` states each contract. Keep them, or change
  them where they are written.
- Code built for a console is hardened (`mk/hardening.mk`), and
  `tests/test_hardening.py` reads it from the built program.
- A new file names its licence in its first lines
  ([licensing](docs/licensing.md)); `tests/test_licensing.py` checks it.
- Explain non-obvious reasons in comments; do not restate the code.
- Say what kind of evidence a claim has: the simulator, a virtual console,
  or a console's hardware.

## Documentation and translations

Documentation is written in English, the technical reference. Some pages
also have a Spanish translation: `NAME.es.md` beside `NAME.md`, each pair
linked both ways by an English / Español line. `docs/translations.json`
lists every translation with the SHA-256 of the English text it was last
reviewed against.

When you change a page that has a translation, update the translation in
the same change if you can, or say in the pull request that it needs one.
`make check` fails until the translation has been reviewed against the new
English text and its `source_sha256` set to the value the check prints; set
it only after reading both. Commands, options, paths, file names, fields
and error codes stay as they are in a translation, and the output of a tool
is quoted in the language the tool prints. Where a translation and its
original differ, the English text holds.

Issues and pull requests are welcome in English or in Spanish.

## Branches, commits and pull requests

1. A short-lived branch from `dev`: `feat/…`, `fix/…`, `docs/…`, `chore/…`.
   Fork the repository unless you have write access.
2. A pull request against `dev` (GitHub proposes `main`: change the base),
   with its template filled in and its checks green, reviewed by the
   maintainer. Pull requests into `dev` are squashed when merged.
3. `main` receives `dev` through a pull request, merged with a merge
   commit, when what is in `dev` is ready to be relied on.

- Use [Conventional Commits](https://www.conventionalcommits.org/) and your
  own name and e-mail in Git: your contribution stays yours.
- Sign off every commit (`git commit -s`, below).
- Inspect `git diff --cached` before committing, and do not rewrite history
  others have.

## Rights and sign-off

The devkit has three licences, by where each part ends up
([licensing](docs/licensing.md)), and a contribution is under the licence
of the part it goes into: as section 5 of the Apache License states, what
you intentionally submit for inclusion is under those terms, with no
additional conditions, unless you explicitly say otherwise. Your
contribution remains yours; you license it, you do not transfer it.

The `Signed-off-by:` line `git commit -s` adds certifies the
[Developer Certificate of Origin 1.1](https://developercertificate.org/):
that you wrote the change or otherwise have the right to submit it under
that licence. Submit only what you may license this way. Code, fonts,
images or sounds from elsewhere keep their own terms: say where they come
from and under which licence, so [what the devkit uses](docs/third-party.md)
can list them. The MUN and Play MUN names and logos are not licensed.

## What stays out of Git

Everything generated lives in `.local/` and in `build/` directories, which
Git ignores: the MUN OS checkout, the engine, builds, card images. This
repository carries no third-party game and no engine: never commit game
data you do not have the right to distribute, an engine's binaries or
source, credentials or personal tool configuration; keep the latter in
`.git/info/exclude` or your global ignore file rather than in `.gitignore`.

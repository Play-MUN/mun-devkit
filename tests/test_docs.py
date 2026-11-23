# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0

"""The documentation's links lead somewhere, and each Spanish page is the
translation of the English page as it is now.

English is the reference. A page that has a translation is `NAME.md` with
`NAME.es.md` beside it; each begins, under its title, with a line that links
the other. `docs/translations.json` records, for every translation, the
SHA-256 of the English text it was last reviewed against: when the English
page changes, this fails until someone has read both and set the new value.
"""

import hashlib
import json
import re
import unittest

from support import ROOT

RECORD = ROOT / "docs" / "translations.json"
# The pages a visitor meets first: these always have a translation.
ALWAYS = ["README.md", "SECURITY.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md"]
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def pages():
    """Every page of documentation in the repository, as paths from its root."""
    found = []
    for path in ROOT.rglob("*.md"):
        parts = path.relative_to(ROOT).parts
        # Not what Git ignores or a developer keeps for themselves: build
        # outputs, and hidden directories other than the repository's own.
        if not any(part == "build" or (part.startswith(".") and part != ".github") for part in parts) \
                and not path.is_symlink():
            found.append(path)
    return sorted(found)


class Links(unittest.TestCase):
    def test_every_link_to_a_file_of_the_repository_finds_it(self):
        broken = []
        for page in pages():
            text = page.read_text(encoding="utf-8")
            for target in LINK.findall(text):
                if re.match(r"[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
                    continue                                   # another site, or a place in this page
                file = (page.parent / target.split("#", 1)[0]).resolve()
                if not file.exists():
                    broken.append(f"{page.relative_to(ROOT)}: {target}")
        self.assertEqual(broken, [])


class Translations(unittest.TestCase):
    def setUp(self):
        self.record = json.loads(RECORD.read_text(encoding="utf-8"))["translations"]

    def test_the_first_pages_are_translated(self):
        for name in ALWAYS:
            self.assertIn(name[:-3] + ".es.md", self.record, name)

    def test_every_spanish_page_is_recorded_and_every_record_has_its_pages(self):
        spanish = sorted(str(page.relative_to(ROOT)) for page in pages() if page.name.endswith(".es.md"))
        self.assertEqual(sorted(self.record), spanish)
        for translation, entry in self.record.items():
            self.assertEqual(entry["source"], translation[:-len(".es.md")] + ".md")
            self.assertTrue((ROOT / entry["source"]).is_file(), entry["source"])

    def test_each_pair_links_the_other_under_its_title(self):
        for translation, entry in self.record.items():
            english, spanish = ROOT / entry["source"], ROOT / translation
            self.assertIn(f"**English** · [Español]({spanish.name})",
                          english.read_text(encoding="utf-8").splitlines()[:4], entry["source"])
            self.assertIn(f"[English]({english.name}) · **Español**",
                          spanish.read_text(encoding="utf-8").splitlines()[:4], translation)

    def test_each_translation_was_reviewed_against_the_english_text_as_it_is(self):
        behind = []
        for translation, entry in sorted(self.record.items()):
            now = hashlib.sha256((ROOT / entry["source"]).read_bytes()).hexdigest()
            if entry["source_sha256"] != now:
                behind.append(f"{translation}: {entry['source']} changed. Read both, bring the translation up to "
                              f"date, then set its source_sha256 in docs/translations.json to {now}")
        self.assertEqual(behind, [])

    def test_a_translation_keeps_the_code_of_its_original(self):
        # Commands, paths, fields and codes are not translated, and a tool's
        # output is quoted as the tool prints it: the blocks of the English
        # page are in the Spanish one unchanged, and so is what it has
        # between backquotes. The comments beside shell commands are prose,
        # and may be translated.
        def code(text):
            blocks = [re.sub(r"\s+#.*$", "", block, flags=re.M) if block.startswith("```sh") else block
                      for block in re.findall(r"^```.*?^```", text, re.M | re.S)]
            prose = " ".join(re.sub(r"^```.*?^```", " ", text, flags=re.M | re.S).split())
            return blocks, set(re.findall(r"`([^`]+)`", prose))

        for translation, entry in sorted(self.record.items()):
            if entry.get("verbatim_from_its_publisher"):
                continue
            blocks, spans = code((ROOT / entry["source"]).read_text(encoding="utf-8"))
            translated_blocks, translated_spans = code((ROOT / translation).read_text(encoding="utf-8"))
            self.assertEqual(translated_blocks, blocks, translation)
            self.assertEqual(sorted(spans - translated_spans), [], translation)


if __name__ == "__main__":
    unittest.main()

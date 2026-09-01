import json
import unittest

import manifest
import version


class DisplayNameTests(unittest.TestCase):
    """Every pack this program builds groups together in the player's list."""

    def test_the_name_carries_the_prefix(self):
        self.assertEqual(manifest.display_name("Sorter"), "Structura: Sorter")

    def test_prefixing_twice_does_not_stack(self):
        once = manifest.display_name("Sorter")
        self.assertEqual(manifest.display_name(once), once)

    def test_the_uuid_ignores_the_prefix(self):
        # the prefix is presentation. Folding it into the UUID would have made
        # every pack built by an older Structura look like a different pack to
        # the game, so an upgrade would leave the player holding two copies.
        self.assertEqual(manifest.pack_uuids("Sorter"),
                         manifest.pack_uuids("Sorter"))
        self.assertNotEqual(manifest.pack_uuids("Sorter"),
                            manifest.pack_uuids("Structura: Sorter"))


class DescriptionTests(unittest.TestCase):
    """The description is one field, so its parts are separated by newlines."""

    def test_the_credits_are_always_last(self):
        text = manifest.build_description()
        self.assertEqual(text.count("\n"), 0)
        self.assertTrue(text.startswith("Structura %s" % version.read()))

    def test_every_part_appears_in_order(self):
        text = manifest.build_description(("north", "south"), "floor 3", "0.2.22")
        lines = text.split("\n")
        self.assertEqual(lines[0], "floor 3")
        self.assertEqual(lines[1], "Nametags: north, south")
        self.assertEqual(lines[2], "TechPack 0.2.22 included")
        self.assertTrue(lines[3].startswith("Structura "))

    def test_the_techpack_line_is_absent_when_it_is_not_bundled(self):
        text = manifest.build_description(("north",), "note", None)
        self.assertNotIn("TechPack", text)

    def test_a_long_note_is_trimmed_rather_than_refused(self):
        text = manifest.build_description(user_text="x" * 200)
        self.assertEqual(text.split("\n")[0], "x" * manifest.DESCRIPTION_LIMIT)

    def test_the_maintainer_is_slime_green_and_the_others_keep_their_colours(self):
        line = manifest.credits_line()
        self.assertIn(manifest.GREEN + "EvilSlimeLabs", line)
        self.assertIn(manifest.ITALIC_PURPLE + "DrAv0011", line)
        self.assertIn(manifest.ITALIC_BLUE + "FondUnicycle", line)
        self.assertIn(manifest.ITALIC_PURPLE + "RavinMaddHatter", line)


class ManifestFileTests(unittest.TestCase):
    def test_the_written_manifest_is_utf8_and_keeps_the_colour_codes(self):
        import tempfile
        import os
        work = tempfile.mkdtemp(prefix="structura-test-")
        try:
            manifest.export(work, "Sorter", nameTags=("a",), user_text="note")
            with open(os.path.join(work, "manifest.json"), encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["header"]["name"], "Structura: Sorter")
            self.assertIn("§a", data["header"]["description"])
            self.assertEqual(data["format_version"], 2)
            self.assertEqual(len(data["modules"]), 1)
            self.assertEqual(data["modules"][0]["type"], "resources")
        finally:
            import shutil
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

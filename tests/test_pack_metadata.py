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

    def test_the_derived_uuid_ignores_the_prefix(self):
        # the prefix is presentation. Folding it into the UUID would have made
        # every pack built by an older Structura look like a different pack.
        self.assertEqual(manifest.derived_pack_uuids("Sorter"),
                         manifest.derived_pack_uuids("Sorter"))
        self.assertNotEqual(manifest.derived_pack_uuids("Sorter"),
                            manifest.derived_pack_uuids("Structura: Sorter"))


class PackIdentityTests(unittest.TestCase):
    """A pack is identified by everything that went into it.

    Deriving the UUID from the name alone made a rebuild an exact duplicate --
    same UUID, same version, because the version is the Structura version -- and
    the game refused the import. Deriving it from the content means an unchanged
    rebuild really is the same pack, and any change is a different one.
    """

    SAMPLE = "name=Sorter|opacity=0.35|model=a1b2"

    def test_the_same_content_gives_the_same_uuid(self):
        self.assertEqual(manifest.pack_uuids("Sorter", self.SAMPLE),
                         manifest.pack_uuids("Sorter", self.SAMPLE))

    def test_any_change_to_the_content_moves_it(self):
        base = manifest.pack_uuids("Sorter", self.SAMPLE)
        for changed in ("name=Sorter|opacity=0.50|model=a1b2",
                        "name=Sorter|opacity=0.35|model=c3d4",
                        "name=Other|opacity=0.35|model=a1b2",
                        self.SAMPLE + "|techpack=0.2.22"):
            with self.subTest(changed=changed):
                self.assertNotEqual(base, manifest.pack_uuids("Sorter", changed))

    def test_the_name_alone_does_not_decide_it(self):
        self.assertNotEqual(manifest.pack_uuids("Sorter", "content one"),
                            manifest.pack_uuids("Sorter", "content two"))

    def test_the_header_and_module_uuids_differ_from_each_other(self):
        header, module = manifest.pack_uuids("Sorter", "anything")
        self.assertNotEqual(header, module)


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


class FingerprintTests(unittest.TestCase):
    """What the pack's identity is actually built from."""

    def make(self, **kw):
        import structura_core
        pack = structura_core.structura.__new__(structura_core.structura)
        pack.display_name = kw.get("name", "Sorter")
        pack.description = kw.get("description", "")
        pack.opacity = kw.get("opacity", 0.35)
        pack.icon = kw.get("icon", "lookups/pack_icon.png")
        pack.tech_pack = kw.get("tech_pack", False)
        pack.big_offset = kw.get("big_offset", None)
        pack.structure_files = kw.get("models", {
            "": {"file": "test_structures/stoneSlabs.mcstructure",
                 "offsets": [0, 0, 0]}})
        return pack.fingerprint()

    def test_the_same_inputs_give_the_same_fingerprint(self):
        self.assertEqual(self.make(), self.make())

    def test_every_setting_that_changes_the_pack_changes_it(self):
        base = self.make()
        for change in ({"name": "Other"}, {"description": "note"},
                       {"opacity": 0.5}, {"tech_pack": True},
                       {"big_offset": [1, 2, 3]},
                       {"models": {"": {"file": "test_structures/rails.mcstructure",
                                        "offsets": [0, 0, 0]}}},
                       {"models": {"": {"file": "test_structures/stoneSlabs.mcstructure",
                                        "offsets": [1, 0, 0]}}}):
            with self.subTest(change=str(change)):
                self.assertNotEqual(base, self.make(**change))

    def test_a_missing_file_does_not_raise(self):
        self.assertIn("absent", self.make(icon="nowhere/at/all.png"))

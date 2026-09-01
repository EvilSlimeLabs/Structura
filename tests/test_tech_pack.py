import unittest

import armor_stand_class
import tech_pack


class ArmorStandMergeTests(unittest.TestCase):
    """Folding a second client entity description into Structura's.

    A client entity file replaces the vanilla one rather than merging with it,
    and between two packs only the higher in the player's list is read, so a
    pack that carries both feature sets has to hold both sets of declarations in
    one file. Structura's own entries have to survive that merge intact.
    """

    def setUp(self):
        self.stand = armor_stand_class.armorstand()
        self.stand.add_model("house")
        self.extra = {
            "materials": {"other": "other_material"},
            "animations": {"spin": "animation.spin",
                           "default_pose": "animation.somebody_elses_pose"},
            "geometry": {"default": "geometry.something_else",
                         "spin": "geometry.spin"},
            "textures": {"spin": "textures/spin"},
            "particle_effects": {"dust": "addon:dust"},
            "scripts": {"animate": ["controller.pose", "spin"],
                        "pre_animation": ["v.x = 1;"],
                        "should_update_bones_and_effects_offscreen": True},
            "render_controllers": ["controller.render.armor_stand",
                                   {"controller.render.spin": "v.spin"}],
        }

    def description(self):
        return self.stand.stand["minecraft:client_entity"]["description"]

    def test_structura_geometry_survives_a_clashing_default(self):
        # the larger render bounds are what keep the model drawing once the
        # stand is off screen; losing them to another pack's default is the
        # one conflict that would break the ghost blocks outright
        self.stand.merge_description(self.extra)
        self.assertEqual(self.stand.geos["default"],
                         "geometry.armor_stand.larger_render")
        self.assertEqual(self.stand.geos["spin"], "geometry.spin")
        self.assertIn("ghost_blocks_house", self.stand.geos)

    def test_structura_animations_win_and_the_rest_are_added(self):
        self.stand.merge_description(self.extra)
        animations = self.description()["animations"]
        self.assertEqual(animations["default_pose"], "animation.armor_stand.default_pose")
        self.assertEqual(animations["spin"], "animation.spin")

    def test_pose_controllers_stay_ahead_of_what_reads_them(self):
        self.stand.merge_description(self.extra)
        animate = self.description()["scripts"]["animate"]
        self.assertEqual(animate[:2], ["controller.pose", "controller.wiggling"])
        self.assertEqual(animate.count("controller.pose"), 1)
        self.assertIn("spin", animate)

    def test_scalars_and_lists_the_stand_lacks_are_taken(self):
        self.stand.merge_description(self.extra)
        scripts = self.description()["scripts"]
        self.assertTrue(scripts["should_update_bones_and_effects_offscreen"])
        self.assertEqual(scripts["pre_animation"], ["v.x = 1;"])

    def test_render_controllers_are_appended_without_duplicates(self):
        self.stand.merge_description(self.extra)
        controllers = self.description()["render_controllers"]
        self.assertEqual(controllers.count("controller.render.armor_stand"), 1)
        self.assertIn("controller.render.armor_stand.ghost_blocks", controllers)
        self.assertIn({"controller.render.spin": "v.spin"}, controllers)

    def test_merging_twice_changes_nothing_further(self):
        self.stand.merge_description(self.extra)
        once = self.description()["scripts"]["animate"][:]
        self.stand.merge_description(self.extra)
        self.assertEqual(self.description()["scripts"]["animate"], once)


@unittest.skipUnless(tech_pack.available(),
                     "be_tech_pack submodule is not checked out")
class TechPackSubmoduleTests(unittest.TestCase):
    """What the real submodule contributes, when it is present."""

    def test_every_animation_the_merge_asks_for_is_declared(self):
        # a short name in scripts.animate that the animations map does not
        # declare is a "can't find animation <name>" in the content log and an
        # animation that silently stops playing. TechPack on its own asks for
        # vanilla's pose controllers without declaring them; merged with
        # Structura, which does declare them, nothing is left dangling.
        stand = armor_stand_class.armorstand()
        stand.add_model("house")
        stand.merge_description(tech_pack.description())
        description = stand.stand["minecraft:client_entity"]["description"]
        declared = set(description["animations"])
        for item in description["scripts"]["animate"]:
            for name in ([item] if isinstance(item, str) else list(item)):
                self.assertIn(name, declared)

    def test_the_shared_geometry_file_is_the_same_asset(self):
        # both projects ship models/entity/armor_stand.larger_render.geo.json
        # and both declare geometry.armor_stand.larger_render. copy_assets
        # skips the file rather than overwriting Structura's, which is only
        # safe while the two are identical.
        import os

        import jsonc
        ours = jsonc.load(os.path.join("lookups", "armor_stand.larger_render.geo.json"))
        theirs = jsonc.load(os.path.join(tech_pack.ROOT, "models", "entity",
                                         "armor_stand.larger_render.geo.json"))
        self.assertEqual(ours, theirs)


if __name__ == "__main__":
    unittest.main()

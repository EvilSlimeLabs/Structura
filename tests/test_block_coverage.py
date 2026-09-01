import json
import re
import unittest

import armor_stand_geo_class as asgc

## Education Edition and other blocks no vanilla pack ships textures for. They
## are declared so a structure containing one is named rather than mysterious,
## and they will never resolve. tools/audit_blocks.py holds the same list.
UNRESOLVABLE = re.compile(r"^(element_\d+|chemistry_table|chemical_heat"
                          r"|hard_(stained_)?glass(_pane)?"
                          r"|colored_torch_\w+|underwater_torch"
                          r"|coral_(fan_)?pink_dead)$")


def load(name):
    with open("lookups/%s.json" % name, encoding="utf-8") as f:
        return json.load(f)


class LookupTableTests(unittest.TestCase):
    """The three tables that describe a block have to agree with each other.

    A block_definition entry naming a shape family that block_shapes does not
    describe raises inside make_block, which _add_blocks_to_geo catches -- so a
    disagreement here does not fail a build, it quietly empties one out of it.
    """

    @classmethod
    def setUpClass(cls):
        cls.defs = load("block_definition")
        cls.shapes = load("block_shapes")
        cls.uv = load("block_uv")

    def test_every_shape_family_is_described_by_both_tables(self):
        families = {v for v in self.defs.values() if v != "ignore"}
        self.assertFalse(families - set(self.shapes),
                         "shape families with no block_shapes entry")
        self.assertFalse(families - set(self.uv),
                         "shape families with no block_uv entry")

    def test_every_shape_variant_has_a_usable_uv_window(self):
        # a variant missing from block_uv silently falls back to "default",
        # which is right only when its cubes are the same size as the default's
        families = {v for v in self.defs.values() if v != "ignore"}
        for family, variants in self.shapes.items():
            if family not in families:
                continue
            for variant, shape in variants.items():
                window = self.uv[family].get(variant, self.uv[family]["default"])
                for face in ("up", "down", "north", "south", "east", "west"):
                    self.assertGreaterEqual(
                        len(window["uv_sizes"][face]), 1,
                        "%s/%s has no %s uv size" % (family, variant, face))
                    self.assertEqual(
                        len(window["uv_sizes"][face]), len(window["offset"][face]),
                        "%s/%s: %s sizes and offsets disagree" % (family, variant, face))


class BlockBuildTests(unittest.TestCase):
    """Blocks that used to be dropped, and the states that dropped them."""

    def setUp(self):
        self.geo = asgc.armorstandgeo("test", offsets=[0, 0, 0])

    def build(self, name, **kwargs):
        self.geo.blocks = {}
        self.geo.make_block(0, 0, 0, name, **kwargs)

    def test_every_defined_block_builds(self):
        defs = load("block_definition")
        broken = []
        for name in defs:
            if UNRESOLVABLE.match(name):
                continue
            try:
                self.build(name)
            except Exception as exc:
                broken.append("%s (%s)" % (name, type(exc).__name__))
        self.assertEqual(broken, [], "blocks that raise in make_block")

    def test_an_unknown_rotation_state_does_not_drop_the_block(self):
        # soul_campfire reads direction 0 against a table that only listed 1,
        # and the block vanished every time it faced that way. A rotation the
        # table cannot describe should leave the block unrotated, not remove it.
        self.build("soul_campfire", rot=0)
        self.build("soul_campfire", rot="nonsense")
        self.assertTrue(self.geo.blocks)

    def test_legacy_slab_ids_build_in_both_halves(self):
        for name in ("stone_slab", "stone_slab2", "stone_slab3", "stone_slab4",
                     "petrified_oak_slab"):
            for top in (False, True):
                self.build(name, top=top)

    def test_the_new_shape_families_build(self):
        for name in ("oak_shelf", "sulfur_spike", "copper_golem_statue",
                     "heavy_core"):
            self.build(name)


if __name__ == "__main__":
    unittest.main()

import unittest

from nbtlib import Byte, String

import armor_stand_geo_class as asgc
from structura_core import structura


class SlabGeometryTests(unittest.TestCase):
    """The two halves of a slab have to agree with each other and with the
    plain cube every other block is built from."""

    def setUp(self):
        self.processor = structura.__new__(structura)
        self.geo = asgc.armorstandgeo("test", alpha=1.0, size=[1, 4, 1], offsets=[0, 0, 0])

    def build(self, name, states, y=0):
        block = {"name": "minecraft:" + name, "states": states}
        rot, top, variant, open_bit, data = self.processor._process_block(block)
        self.geo.blocks = {}
        self.geo.make_block(0, y, 0, name, rot=rot, top=top, variant=variant,
                            trap_open=open_bit, data=data)
        cubes = [c for bone in self.geo.blocks.values() for c in bone["cubes"]]
        self.assertEqual(len(cubes), 1)
        return cubes[0]

    def test_both_halves_use_the_same_footprint_as_a_cube(self):
        cube = self.build("stone", {}, y=0)
        footprint = [cube["size"][0], cube["size"][2]]
        for states in ({"minecraft:vertical_half": String("top")},
                       {"minecraft:vertical_half": String("bottom")},
                       {"top_slot_bit": Byte(1), "wood_type": String("spruce")},
                       {"top_slot_bit": Byte(0), "wood_type": String("spruce")}):
            name = "wooden_slab" if "top_slot_bit" in states else "spruce_slab"
            with self.subTest(states=str(states)):
                slab = self.build(name, states, y=1)
                self.assertEqual([slab["size"][0], slab["size"][2]], footprint)
                self.assertEqual(slab["size"][1], 0.5)

    def test_top_half_sits_half_a_block_above_the_bottom_half(self):
        top = self.build("spruce_slab", {"minecraft:vertical_half": String("top")}, y=2)
        bottom = self.build("spruce_slab", {"minecraft:vertical_half": String("bottom")}, y=2)
        self.assertEqual(top["origin"][1] - bottom["origin"][1], 0.5)
        self.assertEqual(top["origin"][0], bottom["origin"][0])
        self.assertEqual(top["origin"][2], bottom["origin"][2])

    def test_side_faces_take_the_matching_half_of_the_texture(self):
        """V grows downward, so the upper half of the tile belongs on the top
        slab and the lower half on the bottom slab."""
        top = self.build("spruce_slab", {"minecraft:vertical_half": String("top")}, y=3)
        bottom = self.build("spruce_slab", {"minecraft:vertical_half": String("bottom")}, y=3)
        for side in ("north", "south", "east", "west"):
            with self.subTest(side=side):
                self.assertEqual(top["uv"][side]["uv_size"], [1, 0.5])
                self.assertEqual(bottom["uv"][side]["uv_size"], [1, 0.5])
                self.assertEqual(bottom["uv"][side]["uv"][1] - top["uv"][side]["uv"][1], 0.5)


if __name__ == "__main__":
    unittest.main()

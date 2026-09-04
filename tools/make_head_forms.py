"""Give the mob heads a shape, so that they are drawn at all.

    python tools/make_head_forms.py

A head was `ignore`, which is the lookup for a block Structura leaves out on
purpose, so every skull in a build simply was not there and nothing said so.

A head is an eight pixel box wearing an entity sheet: 64x32, with the box
unwrapped across its top left corner the way every mob's head is. Only the top
left 16x16 of a texture becomes a tile, so each face names the window it reads,
and the two windows between them carry all six faces.

Each head is a family of its own because the texture is the only thing that
tells them apart, and `blocks.json` gives every one of them the same name for
it: `skull`, which the vanilla pack points at soul sand. The sheets are copied
out of the community submodule into `textures/entity/skulls/` and named here
directly.

The player head, the dragon head and the piglin head are left out. A player head
wears whatever skin the player has, and neither of the other two has a sheet in
the pack this reads.

Nothing here is needed at run time.
"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import lookup_writer
from make_block_forms import Cube, build

LOOKUPS = os.path.join(ROOT, "structura", "lookups")
SHAPES = os.path.join(LOOKUPS, "block_shapes.json")
UV = os.path.join(LOOKUPS, "block_uv.json")
DEFINITION = os.path.join(LOOKUPS, "block_definition.json")
ROTATION = os.path.join(LOOKUPS, "block_rotation.json")

SHEET = "textures/entity/skulls/%s"

## Which head goes with which block id. The name on the left becomes the family,
## because one family cannot carry four different sheets.
HEADS = {
    "skull_skeleton": ("skeleton", ["skeleton_skull", "skull"]),
    "skull_wither": ("wither_skeleton", ["wither_skeleton_skull"]),
    "skull_zombie": ("zombie", ["zombie_head"]),
    "skull_creeper": ("creeper", ["creeper_head"]),
}

## The head box across the sheet's top left corner: the top and the bottom in a
## row above the four sides. Two 16x16 windows reach all six, and each face
## takes the eight pixel square it needs out of one of them.
FRONT_HALF = (0, 0)      # the top, the right side and the front
BACK_HALF = (16, 0)      # the bottom, the left side and the back


def faces(name):
    """What each face of a head reads, and out of which window."""
    front = SHEET % name + "#0,0"
    back = SHEET % name + "#16,0"
    return ({"up": front, "down": back, "south": front, "north": back,
             "east": front, "west": back},
            {"up": (8, 0, 8, 8), "down": (0, 0, 8, 8),
             "south": (8, 8, 8, 8), "north": (8, 8, 8, 8),
             "east": (0, 8, 8, 8), "west": (0, 8, 8, 8)})


def head(name):
    """A head on the floor, and the same head against a wall.

    The wall form sits against the block behind it and higher up, the way a
    wall sign does: at no rotation that is z 0, facing along +z.
    """
    texture, window = faces(name)
    return {"default": [Cube((8, 8, 8), (4, 0, 4), texture, window=window)],
            "wall": [Cube((8, 8, 8), (4, 4, 0), texture, window=window)]}


## facing_direction: 1 is a head standing on the floor and 2 to 5 name the wall
## it hangs on. The wall values are scoped to the wall form, because 2 means
## something different in the two numberings.
TURNS = {"1": [0, 0, 0],
         "wall:2": [0, 180, 0], "wall:3": [0, 0, 0],
         "wall:4": [0, 90, 0], "wall:5": [0, 270, 0]}


def define(blocks, family):
    table = json.load(io.open(DEFINITION, encoding="utf-8"))
    for block in blocks:
        table[block] = family
    io.open(DEFINITION, "w", encoding="utf-8", newline="").write(
        json.dumps(table, indent="\t", ensure_ascii=False,
                   separators=(",", ":")) + "\n")


def main():
    print("writing the heads")
    for family, (sheet, blocks) in HEADS.items():
        forms = head(sheet)
        shapes, uvs = {}, {}
        for name, cubes in forms.items():
            shapes[name], uvs[name] = build(cubes)
        lookup_writer.put(SHAPES, family, shapes, tight=True)
        lookup_writer.put(UV, family, uvs, tight=True)
        lookup_writer.put(ROTATION, family, TURNS, tight=True)
        define(blocks, family)
        print("   %-16s %s" % (family, ", ".join(blocks)))


if __name__ == "__main__":
    main()

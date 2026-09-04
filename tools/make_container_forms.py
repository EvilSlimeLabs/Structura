"""Give shulker boxes and banners the shape and the sheet they really have.

    python tools/make_container_forms.py

A shulker box was a cube wearing its lid texture on all six faces, because the
only thing `blocks.json` names for it is `shulker_top_<colour>`. It is really a
base with a lid on top, and the whole box is one entity sheet, 64x64 per colour.
Each colour is a family of its own: the sheet is the only thing that tells them
apart, and one family cannot carry seventeen of them.

A banner was `ignore`, so it was not drawn at all. It is a cloth hanging from a
pole, and both are on one sheet. Standing banners turn in sixteen steps like a
sign; wall banners hang off the block behind them.

The sheets are copied out of the community submodule into `textures/entity/`.
Only the top left 16x16 of a texture becomes a tile, so every face names the
window it reads.

**A banner is drawn in its colour but without its patterns.** The colour is in
the block entity, as `Base`, and `tools/make_banner_textures.py` dyes the sheet
once per colour so that each has a texture to read: vanilla tints one white
sheet at run time and a ghost block cannot tint. Patterns are a different
matter. A banner may carry six, each with a colour of its own, which is more
combinations than could be written to disk, so they would have to be composited
while a pack is built and handed to the atlas as a picture rather than a file.

Nothing here is needed at run time. Re-run `tools/make_low_geometry.py`
afterwards.
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


# --- shulker boxes ----------------------------------------------------------
#
# The sheet is the entity one: the lid's top sits at x16 y0, the lid's sides run
# across y16, and the base's sides across y36. The box is drawn as the two parts
# it has, so the lid's art is on the lid and the base's on the base.
SHULKER = "textures/entity/shulker/shulker_%s"

## The dyes that name a block, then below them the ids that name no colour and
## the one whose sheet is spelled differently: Bedrock calls the block light
## gray and the sheet silver, and there is no silver_shulker_box to define.
COLOURS = ["white", "orange", "magenta", "light_blue", "yellow", "lime", "pink",
           "gray", "cyan", "purple", "blue", "brown", "green", "red", "black"]
EXTRA = {"undyed_shulker_box": "undyed", "shulker_box": "undyed",
         "light_gray_shulker_box": "silver"}


def shulker(colour):
    """A base with a lid on it, each reading its own part of the sheet."""
    sheet = SHULKER % colour
    lid = Cube((16, 8, 16), (0, 8, 0), texture={
        "up": sheet + "#16,0", "down": sheet + "#0,16",
        "north": sheet + "#0,16", "south": sheet + "#0,16",
        "east": sheet + "#0,16", "west": sheet + "#0,16"}, window={
        "up": (0, 0, 16, 16), "down": (0, 0, 16, 12),
        "north": (0, 0, 16, 12), "south": (0, 0, 16, 12),
        "east": (0, 0, 16, 12), "west": (0, 0, 16, 12)})
    base = Cube((16, 8, 16), (0, 0, 0), texture={
        "up": sheet + "#0,32", "down": sheet + "#0,48",
        "north": sheet + "#0,32", "south": sheet + "#0,32",
        "east": sheet + "#0,32", "west": sheet + "#0,32"}, window={
        "up": (0, 0, 16, 12), "down": (0, 0, 16, 12),
        "north": (0, 4, 16, 12), "south": (0, 4, 16, 12),
        "east": (0, 4, 16, 12), "west": (0, 4, 16, 12)})
    return {"default": [base, lid]}


# --- banners ----------------------------------------------------------------
#
# A pole with a cloth hanging from it. The sheet holds the cloth across its left
# and the pole up its right, and the cloth is a plane rather than a box: a
# banner is one pixel thick and reading a box unwrap onto it would put the back
# of the cloth on its front.
BANNER = "textures/entity/banner/banner_%s"
CLOTH = {face: (0, 0, 16, 16) for face in
         ("up", "down", "north", "south", "east", "west")}
POLE = {face: (11, 0, 4, 16) for face in
        ("up", "down", "north", "south", "east", "west")}

## The colour is in the block entity, as `Base`, counted in the same order as
## wool, and `core.ENTITY_SHAPES` hands it over as the form to draw. Each form
## names the sheet `tools/make_banner_textures.py` dyed for that colour, because
## the game tints one white sheet at run time and a ghost block cannot tint.
BANNER_COLOURS = ["white", "orange", "magenta", "light_blue", "yellow", "lime",
                  "pink", "gray", "silver", "cyan", "purple", "blue", "brown",
                  "green", "red", "black"]


def standing(sheet):
    """On the floor: a pole up the middle with the cloth hanging in front.

    Vanilla's banner is nearer two blocks tall and stands up out of the one it
    belongs to. This one is kept inside its own block, because a ghost block is
    read as a mark on the place a block goes, and one that leans into its
    neighbours makes a row of banners hard to tell apart.
    """
    return [Cube((2, 16, 2), (7, 0, 7), sheet, window=POLE),
            Cube((14, 13, 0.4), (1, 2, 8.6), sheet, window=CLOTH)]


def wall(sheet):
    """On a wall: the pole lies across the top and the cloth hangs below it.

    Against the block behind it, at z 0, the way a wall sign sits.
    """
    return [Cube((16, 2, 2), (0, 14, 0), sheet, window=POLE),
            Cube((14, 14, 0.4), (1, 0, 2), sheet, window=CLOTH)]


def dyed(shape):
    """One form per colour, and white for a banner with no entity beside it."""
    forms = {str(n): shape(BANNER % colour)
             for n, colour in enumerate(BANNER_COLOURS)}
    forms["default"] = shape(BANNER % "white")
    return forms


STANDING = dyed(standing)
WALL = dyed(wall)

## a standing banner turns in sixteen steps, a wall banner in four
SIXTEEN = {str(n): [0, round(n * 22.5, 1), 0] for n in range(16)}
FOUR = {"2": [0, 180, 0], "3": [0, 0, 0], "4": [0, 90, 0], "5": [0, 270, 0],
        "south": [0, 0, 0], "west": [0, 90, 0], "north": [0, 180, 0],
        "east": [0, 270, 0]}


def define(blocks, family):
    table = json.load(io.open(DEFINITION, encoding="utf-8"))
    for block in blocks:
        table[block] = family
    io.open(DEFINITION, "w", encoding="utf-8", newline="").write(
        json.dumps(table, indent="\t", ensure_ascii=False,
                   separators=(",", ":")) + "\n")


def write(family, forms, rotation=None):
    shapes, uvs = {}, {}
    for name, cubes in forms.items():
        shapes[name], uvs[name] = build(cubes)
    lookup_writer.put(SHAPES, family, shapes, tight=True)
    lookup_writer.put(UV, family, uvs, tight=True)
    if rotation:
        lookup_writer.put(ROTATION, family, rotation, tight=True)


def main():
    print("writing the shulker boxes")
    for colour in COLOURS:
        family = "shulker_box_%s" % colour
        write(family, shulker(colour))
        define(["%s_shulker_box" % colour], family)
    for block, colour in EXTRA.items():
        family = "shulker_box_%s" % colour
        write(family, shulker(colour))
        define([block], family)
    print("   %d colours" % (len(COLOURS) + 1))

    print("writing the banners")
    write("standing_banner", STANDING, SIXTEEN)
    write("wall_banner", WALL, FOUR)
    define(["standing_banner"], "standing_banner")
    define(["wall_banner"], "wall_banner")
    print("   standing and wall, %d colours" % len(BANNER_COLOURS))
    print("now re-run tools/make_low_geometry.py")


if __name__ == "__main__":
    main()

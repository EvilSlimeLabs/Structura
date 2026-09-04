"""Give the blocks that are furniture a shape worth the name.

    python tools/make_furniture_forms.py

A lectern is a stand with a sloped desk on it, an enchanting table is a slab
with a book floating above, a bed is a mattress on legs and a conduit is a small
cage hanging in the middle of its block. Drawn as full cubes, which is what a
lookup with one entry gives them, they read as stone blocks in a row and say
nothing about what they are.

These also carry the states that change what they look like. A bed is two
blocks, head and foot, and the two are not the same shape or the same texture. A
conduit is open when it is powered and closed when it is not. A daylight
detector has a second block id for its inverted form, with a top of its own.

Nothing here is needed at run time. Re-run `tools/make_low_geometry.py`
afterwards: most of these have more than two cubes and want a simple form.
"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import lookup_writer
from make_block_forms import Cube, FACES, build

LOOKUPS = os.path.join(ROOT, "structura", "lookups")
SHAPES = os.path.join(LOOKUPS, "block_shapes.json")
UV = os.path.join(LOOKUPS, "block_uv.json")
DEFINITION = os.path.join(LOOKUPS, "block_definition.json")
ROTATION = os.path.join(LOOKUPS, "block_rotation.json")

BLOCKS = "textures/blocks/%s"


def write(family, forms, center=(8, 8, 8)):
    shapes, uvs = {}, {}
    for name, cubes in forms.items():
        shapes[name], uvs[name] = build(cubes, center)
    lookup_writer.put(SHAPES, family, shapes, tight=True)
    lookup_writer.put(UV, family, uvs, tight=True)
    print("   %-22s %s" % (family, ", ".join(forms)))


def define(blocks, family):
    table = json.load(io.open(DEFINITION, encoding="utf-8"))
    for block in blocks:
        table[block] = family
    body = json.dumps(table, indent="\t", ensure_ascii=False,
                      separators=(",", ":"))
    io.open(DEFINITION, "w", encoding="utf-8", newline="").write(body + "\n")


def turns(family, table):
    """Give a family a rotation entry, numbers and words alike."""
    stored = json.load(io.open(ROTATION, encoding="utf-8"))
    stored[family] = table
    lookup_writer.put(ROTATION, family, table, tight=True)


## the four ways a block that faces one way can be turned, both as Bedrock's
## numbers and as the words newer versions write instead
FACING = {"0": [0, 0, 0], "1": [0, 90, 0], "2": [0, 180, 0], "3": [0, 270, 0],
          "south": [0, 0, 0], "west": [0, 90, 0], "north": [0, 180, 0],
          "east": [0, 270, 0]}


# --- daylight detector ------------------------------------------------------
#
# Three pixels tall, not a cube. The inverted detector is a block id of its own
# rather than a state, and the only thing that tells the two apart is the top:
# `daylight_detector_top` is a list of two, the plain one and the inverted.
DAYLIGHT = {"default": [Cube((16, 6, 16), (0, 0, 0))]}
DAYLIGHT_INVERTED = {"default": [Cube(
    (16, 6, 16), (0, 0, 0),
    texture={"up": BLOCKS % "daylight_detector_inverted_top",
             "down": "default", "north": "default", "south": "default",
             "east": "default", "west": "default"})]}


# --- spore blossom ----------------------------------------------------------
#
# It hangs from the ceiling: a small base against the block above and the
# blossom itself spread flat below it. Not a cube, which is what it was.
SPORE_BLOSSOM = {"default": [
    Cube((4, 3, 4), (6, 13, 6), BLOCKS % "spore_blossom_base"),
    Cube((14, 0.2, 14), (1, 12.8, 1), BLOCKS % "spore_blossom",
         window={face: (1, 1, 14, 14) for face in FACES})]}


# --- lectern ----------------------------------------------------------------
#
# A post on a base with a desk sloped over the top of it. The desk is one box
# leaning back, which is as near as a box model gets to vanilla's wedge.
LECTERN = {"default": [
    Cube((16, 2, 16), (0, 0, 0), BLOCKS % "lectern_base"),
    Cube((8, 10, 8), (4, 2, 4), BLOCKS % "lectern_sides"),
    Cube((16, 4, 14), (0, 12, 1), texture={
        "up": BLOCKS % "lectern_top", "down": BLOCKS % "lectern_base",
        "north": BLOCKS % "lectern_front", "south": BLOCKS % "lectern_sides",
        "east": BLOCKS % "lectern_sides", "west": BLOCKS % "lectern_sides"},
         rotation=(-22, 0, 0))]}


# --- enchanting table -------------------------------------------------------
#
# Three quarters of a block, with the book above it. The book is two leaves
# leaning together, drawn from the table's own top texture: the book's own
# texture is an entity sheet the trimmed pack does not carry.
ENCHANTING = {"default": [
    Cube((16, 12, 16), (0, 0, 0)),
    Cube((8, 0.2, 6), (4, 14, 5), BLOCKS % "enchanting_table_top",
         rotation=(0, 0, 20)),
    Cube((8, 0.2, 6), (4, 14, 5), BLOCKS % "enchanting_table_top",
         rotation=(0, 0, -20))]}


# --- conduit ----------------------------------------------------------------
#
# A small cage in the middle of the block. Its textures are entity sheets rather
# than tiles: conduit_base is 24x12 and the shell 8x8, so each face names the
# window it reads. Powered it opens, unpowered it is a closed shell.
CONDUIT_BASE = BLOCKS % "conduit_base"
CLOSED = BLOCKS % "conduit_closed"
OPEN = BLOCKS % "conduit_open"
SHELL = {face: (0, 0, 8, 8) for face in FACES}

CONDUIT = {
    "0": [Cube((6, 6, 6), (5, 5, 5), CLOSED, window=SHELL)],
    "1": [Cube((4, 4, 4), (6, 6, 6), CONDUIT_BASE,
               window={face: (0, 0, 8, 8) for face in FACES}),
          Cube((8, 8, 8), (4, 4, 4), OPEN, window=SHELL)],
}
CONDUIT["default"] = CONDUIT["0"]


# --- beds -------------------------------------------------------------------
#
# Two blocks, head and foot, each a mattress nine pixels up on two legs. The
# textures are per part and per face, and Bedrock tells the halves apart with
# `head_piece_bit`, which arrives as the shape variant.
def bed(part):
    top = BLOCKS % ("bed_%s_top" % part)
    side = BLOCKS % ("bed_%s_side" % part)
    end = BLOCKS % ("bed_%s_end" % part)
    mattress = Cube((16, 6, 16), (0, 3, 0), texture={
        "up": top, "down": BLOCKS % "planks_oak",
        "north": end, "south": end, "east": side, "west": side})
    legs = [Cube((3, 3, 3), (0, 0, 0), BLOCKS % "planks_oak"),
            Cube((3, 3, 3), (13, 0, 0), BLOCKS % "planks_oak"),
            Cube((3, 3, 3), (0, 0, 13), BLOCKS % "planks_oak"),
            Cube((3, 3, 3), (13, 0, 13), BLOCKS % "planks_oak")]
    return [mattress] + legs


BEDS = {"0": bed("feet"), "1": bed("head")}
BEDS["default"] = BEDS["0"]


def main():
    print("writing the furniture")
    write("daylight", DAYLIGHT)
    write("daylight_inverted", DAYLIGHT_INVERTED)
    define(["daylight_detector_inverted"], "daylight_inverted")

    write("spore_blossom", SPORE_BLOSSOM)
    define(["spore_blossom"], "spore_blossom")

    write("lectern", LECTERN)
    write("enchanting_table", ENCHANTING)
    write("conduit", CONDUIT)
    write("bed", BEDS)
    ## a lectern and a bed both face somewhere; an enchanting table does not
    turns("lectern", FACING)
    turns("bed", FACING)
    print("now re-run tools/make_low_geometry.py")


if __name__ == "__main__":
    main()

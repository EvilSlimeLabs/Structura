"""Give a block a shape for each way it is mounted, and a campfire its flame.

    python tools/make_block_forms.py

Four families take several forms, and the difference between the forms is the
part that holds them up rather than the part everyone looks at. A bell is the
same bell whether it hangs from a beam between two stone posts, from a beam out
of one wall, from a beam spanning two walls, or straight from the block above;
what changes is what carries it. The same is true of a grindstone's legs and of
a hanging sign's chains, and none of it is in the block's own texture: the shape
has to say it.

This writes those forms out. Each variant is a different list of cubes rather
than the same list moved, so the mountings read as different objects.

A campfire also carries its fire here. `extinguished` is the only thing telling
a lit campfire from a dead one, and the logs alone barely differ, so the lit
form gets two crossed quads of the flame texture. That is also what tells a soul
campfire from an ordinary one, because `@up` resolves to whichever fire the
block declares.

The families here own their entries in `lookups/block_shapes.json` and
`lookups/block_uv.json` outright: re-running this replaces them. Nothing here is
needed at run time. Re-run `tools/make_low_geometry.py` afterwards, or the
simplified forms still outline the old shapes.
"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import lookup_writer

SHAPES = os.path.join(ROOT, "structura", "lookups", "block_shapes.json")
UV = os.path.join(ROOT, "structura", "lookups", "block_uv.json")
FACES = ("up", "down", "north", "south", "east", "west")

PX = 1.0 / 16


def px(value):
    """A measurement in pixels, as the fraction of a block the tables hold."""
    return round(value * PX, 6)


class Cube:
    """One box of a block: where it is, how big, and what it is textured with.

    `size` and `at` are in pixels. `texture` is an entry for the UV table's
    overwrite list, so "default" leaves the block's own faces alone, "@up" takes
    whatever the block declares for that face, and a window may travel with it.

    `window` names the part of the texture each face reads, again in pixels, as
    (across, down, wide, tall). Without one the cube is textured by its own
    place in the block, which is what a block drawn from a terrain texture
    wants: the front of a cube sitting in the lower left of the block reads the
    lower left of the tile.
    """

    def __init__(self, size, at, texture="default", window=None, rotation=None):
        self.size = list(size)
        self.at = list(at)
        self.texture = texture
        self.window = window or {}
        self.rotation = rotation

    def shape(self):
        return [px(n) for n in self.size], [px(n) for n in self.at]

    def uv(self, face):
        """The window this face reads, as (offset, size) in tile fractions."""
        if face in self.window:
            across, down, wide, tall = self.window[face]
            return [px(across), px(down)], [px(wide), px(tall)]
        wide, tall, deep = self.size
        across, up, over = self.at
        if face in ("up", "down"):
            return [px(across), px(over)], [px(wide), px(deep)]
        if face in ("north", "south"):
            return [px(across), px(16 - up - tall)], [px(wide), px(tall)]
        return [px(over), px(16 - up - tall)], [px(deep), px(tall)]


def build(cubes, center=(8, 8, 8)):
    """A shapes entry and a UV entry for one list of cubes."""
    shape = {"size": [], "offsets": []}
    uv = {"uv_sizes": {face: [] for face in FACES},
          "offset": {face: [] for face in FACES},
          "overwrite": {face: [] for face in FACES}}
    for cube in cubes:
        size, at = cube.shape()
        shape["size"].append(size)
        shape["offsets"].append(at)
        for face in FACES:
            offset, window = cube.uv(face)
            uv["offset"][face].append(offset)
            uv["uv_sizes"][face].append(window)
            uv["overwrite"][face].append(cube.texture)
    if any(cube.rotation for cube in cubes):
        shape["rotation"] = [list(cube.rotation or (0, 0, 0)) for cube in cubes]
    shape["center"] = [px(n) for n in center]
    return shape, uv


def write(family, forms, center=(8, 8, 8)):
    """Replace one family's shapes and UV windows, one variant at a time."""
    shapes, uvs = {}, {}
    for name, cubes in forms.items():
        shapes[name], uvs[name] = build(cubes, center)
    lookup_writer.put(SHAPES, family, shapes, tight=True)
    lookup_writer.put(UV, family, uvs, tight=True)
    print("   %-18s %s" % (family, ", ".join(forms)))


# --- hanging signs ----------------------------------------------------------
#
# A hanging sign's texture is an entity sized sheet, 64x32, not a terrain tile,
# and it carries three things stacked up the left of it: the bar it hangs from
# at the top, the chains under that, and the board itself from y12 down. Only
# the top left 16x16 of a texture becomes a tile, so each part names the window
# it needs and gets a tile of its own.
BOARD = "@north#0,12"
CHAIN = "@north#0,6"
BAR = "@north#4,0"

## the board, hanging under whatever holds it. 14 wide and 10 deep on the sheet,
## with its edge strip to the left of it and its top edge above.
board = Cube((14, 10, 2), (1, 0, 7), BOARD, window={
    "north": (2, 2, 14, 10), "south": (2, 2, 14, 10),
    "east": (0, 2, 2, 10), "west": (0, 2, 2, 10),
    "up": (2, 0, 14, 2), "down": (2, 0, 14, 2)})

## two chains, reading the chain art rather than the plank art
CHAIN_ART = {face: (0, 0, 2, 6) for face in ("north", "south", "east", "west")}
CHAIN_ART.update({"up": (0, 0, 2, 2), "down": (0, 0, 2, 2)})
chains = [Cube((2, 6, 2), (3, 10, 7), CHAIN, window=CHAIN_ART),
          Cube((2, 6, 2), (11, 10, 7), CHAIN, window=CHAIN_ART)]

## the same two, shortened to make room for a bar above them
STUB_ART = {face: (0, 4, 2, 2) for face in FACES}
stubs = [Cube((2, 4, 2), (3, 10, 7), BAR, window=STUB_ART),
         Cube((2, 4, 2), (11, 10, 7), BAR, window=STUB_ART)]

## the bar a sign is attached to when it hangs straight off the block above
bar = Cube((14, 2, 2), (1, 14, 7), BAR, window={
    "north": (0, 4, 14, 2), "south": (0, 4, 14, 2),
    "east": (0, 4, 2, 2), "west": (0, 4, 2, 2),
    "up": (0, 0, 14, 2), "down": (0, 0, 14, 2)})

## and the arm running back into the wall, on the form mounted on one
arm = Cube((2, 2, 6), (7, 14, 1), BAR, window={
    "north": (0, 4, 2, 2), "south": (0, 4, 2, 2),
    "east": (0, 4, 6, 2), "west": (0, 4, 6, 2),
    "up": (0, 0, 2, 6), "down": (0, 0, 2, 6)})

## Named by attached_bit and hanging, joined the way core.py joins shape states.
## Hanging from a block: chains when it swings free, a bar when it is attached
## to the block. Not hanging: mounted on a wall, which is the bar again with an
## arm back to the wall behind it.
HANGING_SIGNS = {
    "0-1": [board] + chains,
    "1-1": [board] + stubs + [bar],
    "0-0": [board] + stubs + [bar, arm],
    "1-0": [board] + stubs + [bar, arm],
    "default": [board] + chains,
}


# --- bells ------------------------------------------------------------------
#
# The bell itself never changes. Everything above it does. A bell declares its
# beam on the east face and its stone on the west, which is how one entry
# serves every mounting without naming a texture.
BELL_SIDE = "@north"
bell_body = Cube((8, 6, 8), (4, 4, 4))
bell_crown = Cube((4, 3, 4), (6, 10, 6), "@up")
bell_stub = Cube((2, 3, 2), (7, 13, 7), "@up")
bell_beam = Cube((2, 2, 16), (7, 13, 0), "@east")
bell_arm = Cube((2, 2, 8), (7, 13, 0), "@east")
bell_posts = [Cube((2, 13, 2), (7, 0, 1), "@west"),
              Cube((2, 13, 2), (7, 0, 13), "@west")]

BELLS = {
    ## on the floor: a beam across two stone posts
    "standing": [bell_body, bell_crown, bell_beam] + bell_posts,
    ## between two walls: the same beam, carried by them instead
    "multiple": [bell_body, bell_crown, bell_beam],
    ## on one wall: half a beam, out of the wall behind it
    "side": [bell_body, bell_crown, bell_arm],
    ## straight off the block above: no beam at all, just the mount
    "hanging": [bell_body, bell_crown, bell_stub],
    "default": [bell_body, bell_crown, bell_beam] + bell_posts,
}


# --- grindstones ------------------------------------------------------------
#
# The wheel and its two pivots are the block. The legs are what changes: down to
# the floor, up to the block above, or back into the wall it is fixed to.
LEG = "@down"
PIVOT = "@north"
wheel = Cube((12, 8, 4), (2, 6, 6))
pivots = [Cube((2, 3, 4), (1, 7, 6), PIVOT), Cube((2, 3, 4), (13, 7, 6), PIVOT)]
legs_down = [Cube((2, 7, 2), (2, 0, 7), LEG), Cube((2, 7, 2), (12, 0, 7), LEG)]
legs_up = [Cube((2, 7, 2), (2, 9, 7), LEG), Cube((2, 7, 2), (12, 9, 7), LEG)]
legs_back = [Cube((2, 2, 6), (2, 7, 0), LEG), Cube((2, 2, 6), (12, 7, 0), LEG)]
legs_both = legs_back + [Cube((2, 2, 6), (2, 7, 10), LEG),
                         Cube((2, 2, 6), (12, 7, 10), LEG)]

GRINDSTONES = {
    "standing": legs_down + pivots + [wheel],
    "hanging": legs_up + pivots + [wheel],
    "side": legs_back + pivots + [wheel],
    "multiple": legs_both + pivots + [wheel],
    "default": legs_down + pivots + [wheel],
}


# --- campfires --------------------------------------------------------------
#
# Four logs, and the fire above them when it is lit. The fire is two quads
# crossed through the middle of the block, the way vanilla draws every flame,
# and it reads `@up`, which is campfire_fire on a campfire and soul_campfire_fire
# on a soul campfire.
LOG_LIT = "@north"
LOG_OUT = "@down"
FLAME = "@up"

FLAME_ART = {"north": (0, 0, 16, 16), "south": (0, 0, 16, 16),
             "east": (0, 0, 1, 16), "west": (0, 0, 1, 16),
             "up": (0, 0, 16, 1), "down": (0, 0, 16, 1)}


def logs(texture):
    return [Cube((16, 4, 5), (0, 0, 1.5), texture),
            Cube((16, 4, 5), (0, 0, 9.5), texture),
            Cube((5, 4, 16), (1.5, 4, 0), texture),
            Cube((5, 4, 16), (9.5, 4, 0), texture)]


flames = [Cube((12, 10, 1), (2, 6, 7.5), FLAME, window=FLAME_ART,
               rotation=(0, 45, 0)),
          Cube((12, 10, 1), (2, 6, 7.5), FLAME, window=FLAME_ART,
               rotation=(0, -45, 0))]

CAMPFIRES = {
    "0": logs(LOG_LIT) + flames,        # burning
    "1": logs(LOG_OUT),                 # out
    "default": logs(LOG_LIT) + flames,
}


def main():
    print("writing the mounted forms")
    write("hanging_sign", HANGING_SIGNS)
    write("bell", BELLS)
    ## the grindstone turns about the wheel's own height rather than the middle
    ## of the block, which is where its entry has always put the pivot
    write("grindstone", GRINDSTONES, center=(8, 7.04, 8))
    write("campfire", CAMPFIRES, center=(8, 4, 8))

    ## the bell's own faces belong on the bell, not the beam's planks and not
    ## the posts' stone, so its side faces are pinned to bell_side
    entry = json.load(io.open(UV, encoding="utf-8"))["bell"]
    for variant in entry:
        for face in ("east", "west"):
            entry[variant]["overwrite"][face][0] = BELL_SIDE
    lookup_writer.put(UV, "bell", entry, tight=True)
    print("   %-18s bell_side on the body's own sides" % "bell")


if __name__ == "__main__":
    main()

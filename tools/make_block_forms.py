"""Give a block a shape it cannot be read off a terrain tile with.

    python tools/make_block_forms.py

Several families take more than one form, and the difference between the forms
is the
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

The shelf is here for the other reason a block cannot be read off a terrain
tile: its texture is a sheet with a different picture for each face, and taking
the whole of it paints the front's compartments onto all six. A door is the
narrow version of the same thing: three pixels thick, and every one of its six
faces was reading the whole of the door's picture, so the panel was squeezed
into each edge.

The tripwire hook is here for a third reason: `attached_bit` says whether
anything is tied to it, and the hook hanging loose off its plate is a different
arrangement of the same three pieces from the hook held out level by a wire.

The shelf, the sculk shrieker and string are here for a fourth: a ghost block is
half transparent, and vanilla's own way of drawing them does not survive that. A
shelf's compartments are painted into its front texture, which reads as a shelf
on a solid block and as a plain box on a see-through one, so they are cut here
instead. A shrieker is half a block tall with a hole in the middle of its lid,
and drawn from the terrain tiles as a full cube it is a block of sculk with a
transparent top. String lies flat rather than filling its block, and wears a
tile `tools/make_string_texture.py` draws for it. A flower pot is hollow, and
one cube of the compost tile is a brown block with nothing pot shaped about it.

The brewing stand, the bell and the heavy core are here for the same reason from
the other end: their tiles hold more than the part any one face wants. A brewing
stand's rod is drawn down the middle of its tile with the arms that hold the
bottles either side of it, the bell is an eight by nine picture in a sixteen by
sixteen file, the heavy core's file holds three eight by eight pictures and an
empty quarter, and every one of a dried ghast's twenty four textures is a ten by
ten picture in a sixteen by sixteen file. A face taking the whole tile wears the
wrong thing or nothing at all.

Both pots are here for a fifth reason as well: what look like their terrain
tiles are sheets. A face left to work its own window out reads the whole of one
as if it were a single picture, which puts the decorated pot's shoulder on the
unwrap of its neck and takes the flower pot's wall from the rim. `on_sheet`
turns a region of a sheet into the reference and the window a face needs.

The families here own their entries in `lookups/block_shapes.json` and
`lookups/block_uv.json` outright: re-running this replaces them. Nothing here is
needed at run time. Re-run `tools/make_low_geometry.py` afterwards, or the
simplified forms still outline the old shapes.
"""
import io
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import lookup_writer

SHAPES = os.path.join(ROOT, "structura", "lookups", "block_shapes.json")
UV = os.path.join(ROOT, "structura", "lookups", "block_uv.json")
DEFINITION = os.path.join(ROOT, "structura", "lookups", "block_definition.json")
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

    def paint(self, face):
        """The texture this face takes, which may differ from face to face."""
        if isinstance(self.texture, dict):
            return self.texture[face]
        return self.texture

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
            uv["overwrite"][face].append(cube.paint(face))
    if any(cube.rotation for cube in cubes):
        shape["rotation"] = [list(cube.rotation or (0, 0, 0)) for cube in cubes]
    shape["center"] = [px(n) for n in center]
    return shape, uv


def spun(point, pivot, rotation):
    """`point` turned about `pivot` the way a bone's rotation turns its cubes.

    Bedrock's angles run the other way round from the usual mathematical ones:
    a positive value turns clockwise in the plane it names. The piglin's ears
    are what settles that, because only one of the two signs takes them away
    from the head rather than into it.

    Every turn read here is about a single axis, so the order the three are
    applied in does not come up.
    """
    x, y, z = (a - b for a, b in zip(point, pivot))
    rx, ry, rz = (math.radians(-angle) for angle in rotation)
    y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
    z, x = z * math.cos(ry) - x * math.sin(ry), z * math.sin(ry) + x * math.cos(ry)
    x, y = x * math.cos(rz) - y * math.sin(rz), x * math.sin(rz) + y * math.cos(rz)
    return [x + pivot[0], y + pivot[1], z + pivot[2]]


def unwrap(uv, size):
    """The six rectangles of the sheet a box of an entity model reads.

    Bedrock lays a box out from its UV corner as two faces in a row above four
    in a strip: up and down across the top, then west, the front, east and the
    back. The front is named south here because the model is turned half a turn
    on the way into a block, which is what puts it on the block's south face.
    """
    wide, tall, deep = size
    u, v = uv
    return {
        "up": (u + deep, v, wide, deep),
        "down": (u + deep + wide, v, wide, deep),
        "west": (u, v + deep, deep, tall),
        "south": (u + deep, v + deep, wide, tall),
        "east": (u + deep + wide, v + deep, deep, tall),
        "north": (u + deep + wide + deep, v + deep, wide, tall),
    }


def define(blocks, family):
    """Point block ids at a family, leaving the rest of the file alone."""
    table = json.load(io.open(DEFINITION, encoding="utf-8"))
    for block in blocks:
        table[block] = family
    ## the file is one key a line, tab indented, with no space after the colon;
    ## writing it any other way reformats three thousand lines
    body = json.dumps(table, indent="\t", ensure_ascii=False,
                      separators=(",", ":"))
    io.open(DEFINITION, "w", encoding="utf-8", newline="").write(body + "\n")


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

## the same bar, run out to the edges of the block so that it reaches the wall
## it is fixed to. The form under a block has nothing to reach and stays 14.
wall_bar = Cube((16, 2, 2), (0, 14, 7), BAR, window={
    "north": (0, 4, 14, 2), "south": (0, 4, 14, 2),
    "east": (0, 4, 2, 2), "west": (0, 4, 2, 2),
    "up": (0, 0, 14, 2), "down": (0, 0, 14, 2)})

## Named by attached_bit and hanging, joined the way core.py joins shape states.
## Hanging from a block: chains when it swings free, a bar when it is attached
## to the block. Not hanging: mounted on a wall, where the bar itself reaches
## the wall, the way a bell's beam spans two of them. A second piece running
## back into the wall reads as a post nobody asked for.
HANGING_SIGNS = {
    "0-1": [board] + chains,
    "1-1": [board] + stubs + [bar],
    "0-0": [board] + stubs + [wall_bar],
    "1-0": [board] + stubs + [wall_bar],
    "default": [board] + chains,
}


# --- bells ------------------------------------------------------------------
#
# The bell itself never changes. Everything above it does. A bell declares four
# different things on its six faces, which is how one entry serves every
# mounting without naming a texture: the bell on north and south, its crown on
# up, its rim on down, the beam's planks on east and the posts' stone on west.
BELL_SIDE = "@north"        # bell_side
BELL_TOP = "@up"            # bell_top
BELL_RIM = "@down"          # bell_bottom
BELL_WOOD = "@east"         # dark oak planks, whatever holds the bell up
BELL_STONE = "@west"        # the posts a standing bell hangs between

## `bell_side` draws the whole bell down one column of its tile: the narrow
## body, six across and seven down, over the flared lip, eight across and two
## down. `bell_top` and `bell_bottom` are the eight by eight faces at each end.
## Faces left to work their own window out read the middle of the tile, which
## for an eight by eight picture in a sixteen by sixteen file is mostly nothing,
## and the bell comes out as a flat plate.
BODY_WIDE, BODY_TALL = 6, 7
LIP_WIDE, LIP_TALL = 8, 2
BELL_FLOOR = 4              # so the bell's crown meets the beam at 13


def bell_piece(size, at, side_window, cap_window):
    """One of the bell's two parts, reading its own rows of the side tile."""
    wide, tall, _deep = size
    return Cube(size, at, texture={
        "north": BELL_SIDE, "south": BELL_SIDE,
        "east": BELL_SIDE, "west": BELL_SIDE,
        "up": BELL_TOP, "down": BELL_RIM}, window={
        "north": side_window, "south": side_window,
        "east": side_window, "west": side_window,
        "up": cap_window, "down": cap_window})


bell_lip = bell_piece(
    (LIP_WIDE, LIP_TALL, LIP_WIDE),
    ((16 - LIP_WIDE) // 2, BELL_FLOOR, (16 - LIP_WIDE) // 2),
    (0, BODY_TALL, LIP_WIDE, LIP_TALL), (0, 0, LIP_WIDE, LIP_WIDE))
bell_body = bell_piece(
    (BODY_WIDE, BODY_TALL, BODY_WIDE),
    ((16 - BODY_WIDE) // 2, BELL_FLOOR + LIP_TALL, (16 - BODY_WIDE) // 2),
    (1, 0, BODY_WIDE, BODY_TALL), (1, 1, BODY_WIDE, BODY_WIDE))

## and what carries it. The short bar under a ceiling is the same dark oak as
## every beam; it wore the bell's own crown texture and came out gold.
bell_stub = Cube((2, 3, 2), (7, 13, 7), BELL_WOOD)
bell_beam = Cube((2, 2, 16), (7, 13, 0), BELL_WOOD)
bell_arm = Cube((2, 2, 8), (7, 13, 0), BELL_WOOD)
bell_posts = [Cube((2, 13, 2), (7, 0, 1), BELL_STONE),
              Cube((2, 13, 2), (7, 0, 13), BELL_STONE)]

BELL = [bell_lip, bell_body]

BELLS = {
    ## on the floor: a beam across two stone posts
    "standing": BELL + [bell_beam] + bell_posts,
    ## between two walls: the same beam, carried by them instead
    "multiple": BELL + [bell_beam],
    ## on one wall: half a beam, out of the wall behind it
    "side": BELL + [bell_arm],
    ## straight off the block above: no beam at all, just the mount
    "hanging": BELL + [bell_stub],
    "default": BELL + [bell_beam] + bell_posts,
}


# --- grindstones ------------------------------------------------------------
#
# The wheel and its two pivots are the block. The legs are what changes: down to
# the floor, up to the block above, or back into the wall it is fixed to.
#
# **The wheel is the size its own textures were drawn for.** `grindstone_side`
# is twelve across and twelve down and `grindstone_round` is eight across and
# twelve down, which is a wheel twelve wide, twelve tall and eight deep seen
# face on and then edge on. It was drawn twelve by eight by four, a third of the
# stone that should be there.
#
# And it names its faces. `blocks.json` puts `grindstone_pivot` on north and
# the leg's oak on down, because those are slots the engine picks from for its
# own model rather than the six sides of a cube, so a wheel left to the block's
# own faces has a pivot painted on its back and a log on its underside.
LEG = "@down"               # log_big_oak
PIVOT = "@north"            # grindstone_pivot
STONE_FACE = "@east"        # grindstone_side, the wheel face on
STONE_EDGE = "@up"          # grindstone_round, the same wheel edge on
WHEEL_WIDE, WHEEL_TALL, WHEEL_DEEP = 12, 12, 8
WHEEL_AT = (16 - WHEEL_WIDE) // 2       # the pivots stand just outside it
WHEEL_Z = (16 - WHEEL_DEEP) // 2
PIVOT_TALL = 4
LEG_ROOM = 16 - WHEEL_TALL              # what the block has left for the legs


def grindstone(floor, legs):
    """The wheel at a height, its two pivots at the axle, and its legs.

    The wheel takes three quarters of the block, so where it sits is what the
    mounting decides: on the floor it stands on legs and everything is that much
    higher, under a block it hangs from them, and against a wall it is in the
    middle with the legs running back into the wall.
    """
    axle = floor + WHEEL_TALL // 2
    wheel = Cube((WHEEL_WIDE, WHEEL_TALL, WHEEL_DEEP), (WHEEL_AT, floor, WHEEL_Z),
                 texture={"north": STONE_FACE, "south": STONE_FACE,
                          "east": STONE_EDGE, "west": STONE_EDGE,
                          "up": STONE_EDGE, "down": STONE_EDGE},
                 window={"north": (0, 0, WHEEL_WIDE, WHEEL_TALL),
                         "south": (0, 0, WHEEL_WIDE, WHEEL_TALL),
                         "east": (0, 0, WHEEL_DEEP, WHEEL_TALL),
                         "west": (0, 0, WHEEL_DEEP, WHEEL_TALL),
                         "up": (0, 0, WHEEL_DEEP, WHEEL_DEEP),
                         "down": (0, 0, WHEEL_DEEP, WHEEL_DEEP)})
    pivots = [Cube((2, PIVOT_TALL, 4), (at, axle - PIVOT_TALL // 2, 6), PIVOT)
              for at in (WHEEL_AT - 2, WHEEL_AT + WHEEL_WIDE)]
    return legs(floor, axle) + pivots + [wheel]


def legs_down(_floor, _axle):
    return [Cube((2, LEG_ROOM, 2), (at, 0, 7), LEG)
            for at in (WHEEL_AT, 16 - WHEEL_AT - 2)]


def legs_up(floor, _axle):
    return [Cube((2, LEG_ROOM, 2), (at, floor + WHEEL_TALL, 7), LEG)
            for at in (WHEEL_AT, 16 - WHEEL_AT - 2)]


def legs_back(_floor, axle, sides=(0,)):
    return [Cube((2, 2, 6), (at, axle - 1, z), LEG)
            for z in sides for at in (WHEEL_AT, 16 - WHEEL_AT - 2)]


GRINDSTONES = {
    ## on the floor, so the wheel is up against the block above it
    "standing": grindstone(LEG_ROOM, legs_down),
    ## under a block, so it hangs and the wheel is down against the floor
    "hanging": grindstone(0, legs_up),
    ## on a wall, so the wheel sits in the middle and the legs run into it
    "side": grindstone(LEG_ROOM // 2, legs_back),
    "multiple": grindstone(LEG_ROOM // 2,
                           lambda floor, axle: legs_back(floor, axle, (0, 10))),
    "default": grindstone(LEG_ROOM, legs_down),
}


# --- campfires --------------------------------------------------------------
#
# Four logs, and the fire above them when it is lit. The fire is two quads
# crossed through the middle of the block, the way vanilla draws every flame,
# and it reads `@up`, which is campfire_fire on a campfire and soul_campfire_fire
# on a soul campfire.
#
# The log tile is three pictures stacked, not one: the bark across the top four
# rows, the cut end of a log beside it in the next four, and the ash the fire
# sits in across the bottom half. A face taking the whole tile wears all three.
#
# The ash is a plate one pixel deep across the floor of the block, and the logs
# stand on it rather than above it: the pair underneath is four across at x1 and
# x11 running the depth of the block, and the pair over them is four deep at z1
# and z11 running the width, so the ash shows through the square between them.
LOG_LIT = "@north"
LOG_OUT = "@down"
FLAME = "@up"

FLAME_ART = {"north": (0, 0, 16, 16), "south": (0, 0, 16, 16),
             "east": (0, 0, 1, 16), "west": (0, 0, 1, 16),
             "up": (0, 0, 16, 1), "down": (0, 0, 16, 1)}

LOG_BARK = (0, 0, 16, 4)        # the length of a log
LOG_END = (0, 4, 4, 4)          # its cut face
ASH = (0, 8, 16, 8)             # what the logs sit in
LOG_THICK = 4
ASH_DEEP = 1


def log(size, at, texture):
    """One log, its ends reading the cut face and its length the bark.

    A log lying along z has a top four across and sixteen deep, and the bark is
    drawn the other way round; there is no turning a window, so it takes the
    bark as it is. That face is under the pair above it or on the floor.
    """
    wide, _tall, deep = size
    along_x = wide > deep
    return Cube(size, at, texture, window={
        "north": LOG_BARK if along_x else LOG_END,
        "south": LOG_BARK if along_x else LOG_END,
        "east": LOG_END if along_x else LOG_BARK,
        "west": LOG_END if along_x else LOG_BARK,
        "up": LOG_BARK, "down": LOG_BARK})


def logs(texture):
    """The ash, the pair of logs in it, and the pair across those."""
    return [
        Cube((16, ASH_DEEP, 16), (0, 0, 0), texture, window={
            "up": ASH, "down": ASH,
            "north": (0, 15, 16, ASH_DEEP), "south": (0, 15, 16, ASH_DEEP),
            "east": (0, 15, 16, ASH_DEEP), "west": (0, 15, 16, ASH_DEEP)}),
        log((LOG_THICK, LOG_THICK, 16), (1, 0, 0), texture),
        log((LOG_THICK, LOG_THICK, 16), (16 - 1 - LOG_THICK, 0, 0), texture),
        log((16, LOG_THICK, LOG_THICK), (0, LOG_THICK, 1), texture),
        log((16, LOG_THICK, LOG_THICK), (0, LOG_THICK, 16 - 1 - LOG_THICK),
            texture),
    ]


flames = [Cube((12, 10, 1), (2, 6, 7.5), FLAME, window=FLAME_ART,
               rotation=(0, 45, 0)),
          Cube((12, 10, 1), (2, 6, 7.5), FLAME, window=FLAME_ART,
               rotation=(0, -45, 0))]

CAMPFIRES = {
    "0": logs(LOG_LIT) + flames,        # burning
    "1": logs(LOG_OUT),                 # out
    "default": logs(LOG_LIT) + flames,
}


# --- doors ------------------------------------------------------------------
#
# A door is a panel three pixels thick, and every one of its six faces was
# reading the whole of the door's picture. On the two big faces that is right.
# On the four thin ones it squeezes the whole door into three pixels, which is
# what put a row of panels down each edge and across the top. An edge is the
# frame down the side of the tile, three across and the height of the door.
#
# **The panel sits on the side the door faces**, the way it does in the game:
# placed from the south, a door faces south and its panel is at z13. It was at
# z0, so every door was drawn against the far side of its own block.
#
# **And it turns about the middle of the block**, like everything else. The
# pivot was on the panel's own plane, so a door turned a quarter of the way
# round swung out of its block entirely.
DOOR_THICK = 3
DOOR_LOWER = "@down"            # door_lower, the half nearest the floor
DOOR_UPPER = "@north"           # door_upper, declared on `side`
DOOR_WHOLE = (0, 0, 16, 16)
DOOR_EDGE = (0, 0, DOOR_THICK, 16)          # the frame down one side
DOOR_TOP = (0, 0, 16, DOOR_THICK)           # and across the top of it
DOOR_FOOT = (0, 16 - DOOR_THICK, 16, DOOR_THICK)


def door_half(at, texture, along_x):
    """One block of a door, its edges reading the frame and not the panel."""
    if along_x:
        size = (16, 16, DOOR_THICK)
        window = {"north": DOOR_WHOLE, "south": DOOR_WHOLE,
                  "east": DOOR_EDGE, "west": DOOR_EDGE,
                  ## a top face sixteen across and three deep cannot read a
                  ## frame three across and sixteen down without turning it, so
                  ## it takes the top of the door's own picture instead
                  "up": DOOR_TOP, "down": DOOR_FOOT}
    else:
        size = (DOOR_THICK, 16, 16)
        window = {"east": DOOR_WHOLE, "west": DOOR_WHOLE,
                  "north": DOOR_EDGE, "south": DOOR_EDGE,
                  "up": DOOR_EDGE, "down": DOOR_EDGE}
    return Cube(size, at, texture, window=window)


def door(x, z, along_x):
    """Both halves of a door. The lower block draws them; the upper draws
    nothing, which is what the `top` variant is for."""
    return [door_half((x, 0, z), DOOR_LOWER, along_x),
            door_half((x, 16, z), DOOR_UPPER, along_x)]


DOORS = {
    ## shut, on the side of the block the door faces
    "default": door(0, 16 - DOOR_THICK, True),
    ## open, folded back against the wall on whichever side the hinge is
    "open": door(0, 0, False),
    "open_hinged": door(16 - DOOR_THICK, 0, False),
    ## the upper block of a door draws nothing at all: a cube of nothing rather
    ## than no cube, because the tables are read by the variant existing
    "top": [Cube((0.016, 0.016, 0.016), (0, 0, 0))],
}


# --- shelves ----------------------------------------------------------------
#
# A shelf's texture is a 32x32 sheet holding the four different things its faces
# show: the front, with three compartments painted into it, top left; the solid
# back beside it; and plain planks across the bottom half for the top, the
# bottom and the two ends. The regions are exactly the unwrap of a box 16 wide,
# 16 tall and 8 deep, which is what a shelf is. Vanilla paints the compartments
# rather than cutting them, which is why the front carries their shading.
#
# It hangs on the wall behind it, so it fills the back half of its block: at no
# rotation that is z 0 to 8, the same way a wall sign sits at z 0 to 2.
SHELF_FRONT = "@north#0,0"
SHELF_BACK = "@north#16,0"
SHELF_FLAT = "@north#0,16"      # the top and the bottom, one above the other
SHELF_END = "@north#16,16"      # the two ends, side by side

# The compartments are cut rather than painted. Vanilla paints them into the
# front texture and leaves the block a plain box, which is right for a solid
# block seen from outside and wrong for a half-transparent one: a ghost shelf
# drawn as a box is a box, and nothing about it says shelf. The frame and the
# two dividers are drawn instead, and the back panel keeps the painted front so
# the compartments still have their shading inside.
BACK_DEEP = 2       # the panel against the wall
FRAME = 4           # the rail across the top and the bottom
DIVIDERS = (5, 10)  # where the two uprights stand, from the front texture


def shelf_piece(size, at, front_window):
    """One piece of the frame, reading its own slice of each part of the sheet.

    `front_window` is where the piece sits on the front, in texture pixels, and
    the back takes the same window of the back. The flat tile holds the top over
    the bottom and the end tile holds one end beside the other, so the faces
    that read them take a slice the size of the face.
    """
    wide, tall, deep = size
    return Cube(size, at, texture={
        "south": SHELF_FRONT, "north": SHELF_BACK,
        "up": SHELF_FLAT, "down": SHELF_FLAT,
        "east": SHELF_END, "west": SHELF_END}, window={
        "south": front_window, "north": front_window,
        "up": (at[0], 0, wide, deep), "down": (at[0], 8, wide, deep),
        "east": (0, 16 - at[1] - tall, deep, tall),
        "west": (8, 16 - at[1] - tall, deep, tall)})


SHELVES = {"default": [
    ## the panel against the wall, carrying the painted front so that the
    ## compartments keep their shading behind the frame
    Cube((16, 16, BACK_DEEP), (0, 0, 0), texture={
        "south": SHELF_FRONT, "north": SHELF_BACK,
        "up": SHELF_FLAT, "down": SHELF_FLAT,
        "east": SHELF_END, "west": SHELF_END}, window={
        "south": (0, 0, 16, 16), "north": (0, 0, 16, 16),
        "up": (0, 0, 16, BACK_DEEP), "down": (0, 8, 16, BACK_DEEP),
        "east": (0, 0, BACK_DEEP, 16), "west": (8, 0, BACK_DEEP, 16)}),
    shelf_piece((16, FRAME, 8 - BACK_DEEP), (0, 0, BACK_DEEP),
                (0, 16 - FRAME, 16, FRAME)),
    shelf_piece((16, FRAME, 8 - BACK_DEEP), (0, 16 - FRAME, BACK_DEEP),
                (0, 0, 16, FRAME)),
] + [
    shelf_piece((1, 16 - 2 * FRAME, 8 - BACK_DEEP), (x, FRAME, BACK_DEEP),
                (x, FRAME, 1, 16 - 2 * FRAME))
    for x in DIVIDERS
]}


# --- sculk shriekers --------------------------------------------------------
#
# A sculk shrieker is half a block tall, not a full one, and the hole in the
# middle of its top is a hole in the texture: `sculk_shrieker_top` is four
# corner blobs with nothing between them, and the game draws
# `sculk_shrieker_inner_top` under it so there is something to see down the
# throat. Drawn as a full cube from the terrain tiles, a shrieker is a block of
# sculk with a transparent lid.
SHRIEKER_TALL = 8
SHRIEKER_INNER = "textures/blocks/sculk_shrieker_inner_top"

SHRIEKERS = {"default": [
    Cube((16, SHRIEKER_TALL, 16), (0, 0, 0)),
    ## the throat, a hair under the lid so the two do not fight over the plane
    Cube((16, 1, 16), (0, SHRIEKER_TALL - 1.5, 0), texture=SHRIEKER_INNER,
         window={face: (0, 0, 16, 16) for face in FACES}),
]}


# --- string -----------------------------------------------------------------
#
# String lies flat on the floor of its block, a pixel or so up, and is one quad
# rather than the cube the tables drew it as. `tools/make_string_texture.py`
# writes the tile it wears, because vanilla's is a scatter of faint single
# pixels that cannot be seen on a half-transparent plate.
STRING = "textures/blocks/structura_string"
STRING_UP = 1.5

STRINGS = {"default": [
    Cube((16, 0.5, 16), (0, STRING_UP, 0), texture=STRING,
         window={face: (0, 0, 16, 16) for face in FACES}),
]}


# --- tripwire hooks ---------------------------------------------------------
#
# A tripwire hook is a plank plate against the wall with a metal hook on it, and
# `attached_bit` says which of two things the hook is doing: hanging straight
# down off the plate with nothing on it, or held out horizontally by the wire it
# is tied to. That is a different arrangement of the same three pieces rather
# than one shape turned, so each gets its own list.
#
# It hangs on the wall behind it, so the plate sits at z 0 to 2, the same way a
# wall sign does, and the hook reaches out towards +z.
#
# `blocks.json` gives the block three textures and the pieces take two of them:
# `@down` is trip_wire_base, which is oak planks, and `@north` is
# trip_wire_source, which holds the hook drawn face on. That tile is the hook at
# rest: the ring across x5 to x11 at the top, and the shaft hanging below it
# down the middle, which is where the windows below read from.
HOOK = "@north"
HOOK_RING = (5, 3, 6, 6)        # the ring, face on
HOOK_SHAFT = (7, 9, 2, 6)       # the shaft below it
HOOK_END = (7, 9, 2, 2)         # a square of the shaft, for its small faces

## the plank plate, flush against the wall. The same in both forms.
plate = Cube((6, 6, 2), (5, 6, 0), texture="@down")


def ring(at):
    """The hook's ring, face on to whoever is looking at the block."""
    return Cube((6, 6, 2), at, texture=HOOK, window={
        "north": HOOK_RING, "south": HOOK_RING,
        "east": HOOK_SHAFT, "west": HOOK_SHAFT,
        "up": (5, 3, 6, 2), "down": (5, 3, 6, 2)})


def shaft(size, at):
    """The bar the ring hangs from, upright or reaching out.

    The tile draws it upright, so the long faces read the whole strip and the
    small square ends read a square of it.
    """
    wide, tall, deep = size
    return Cube(size, at, texture=HOOK, window={
        face: (HOOK_SHAFT if tall > deep and face not in ("up", "down")
               else HOOK_END)
        for face in FACES})


TRIPWIRE_HOOKS = {
    ## nothing tied to it: the ring sits on the plate and the shaft hangs
    "0": [plate, ring((5, 6, 2)), shaft((2, 6, 2), (7, 0, 2))],
    ## tied to a wire, which holds the hook out level with the plate
    "1": [plate, shaft((2, 2, 6), (7, 8, 2)), ring((5, 6, 7))],
}
TRIPWIRE_HOOKS["default"] = TRIPWIRE_HOOKS["0"]


# --- dried ghasts -----------------------------------------------------------
#
# All twenty four of its textures are ten by ten pictures in sixteen by sixteen
# files, one set per `rehydration_level`. The block was a fourteen by fourteen
# cube whose faces worked their own windows out from where it sat, so every one
# of them read x1 to x15 of a picture that stops at x10 and the ghast came out
# as a handful of slivers rather than a body.
#
# It is that ten by ten picture's own cube, standing on the floor of the block
# with six tentacles lying flat on the ground around it: two out of each of its
# three blank sides, and none out of the face. Each is three long, two across
# and one deep, and they sit 2 pixels in from the corners of the body.
#
# The tentacles keep the block's own faces, so they follow the rehydration level
# with the rest of it.
GHAST_WIDE = 10
GHAST_ART = (0, 0, GHAST_WIDE, GHAST_WIDE)
GHAST_AT = (16 - GHAST_WIDE) // 2
TENTACLE_LONG = 3
TENTACLE_WIDE = 2
TENTACLE_TALL = 1
## how far along a side each of its two tentacles starts, from the near corner
## of the body
TENTACLE_IN = 2
## a patch of the underside, which is the pale the tentacles are
TENTACLE_ART = (4, 4)


def tentacle(at, along_x):
    """One tentacle, lying flat on the ground out of one side of the body.

    Every face reads a patch of the block's underside the size of that face, so
    the pale runs at the same pixel scale as the rest of the block.
    """
    size = ((TENTACLE_LONG, TENTACLE_TALL, TENTACLE_WIDE) if along_x
            else (TENTACLE_WIDE, TENTACLE_TALL, TENTACLE_LONG))
    wide, tall, deep = size
    across, down = TENTACLE_ART
    return Cube(size, at, "@down", window={
        "up": (across, down, wide, deep), "down": (across, down, wide, deep),
        "north": (across, down, wide, tall),
        "south": (across, down, wide, tall),
        "east": (across, down, deep, tall),
        "west": (across, down, deep, tall)})


def dried_ghast():
    far = GHAST_AT + GHAST_WIDE
    ## the two along a side, a pixel in from each corner of the body
    spread = (GHAST_AT + TENTACLE_IN,
              far - TENTACLE_IN - TENTACLE_WIDE)
    tentacles = []
    for near in spread:
        ## out of the west side and the east side
        tentacles.append(tentacle((GHAST_AT - TENTACLE_LONG, 0, near), True))
        tentacles.append(tentacle((far, 0, near), True))
        ## and out of the back, which is north; the face is south and has none
        tentacles.append(tentacle((near, 0, GHAST_AT - TENTACLE_LONG), False))
    body = Cube((GHAST_WIDE, GHAST_WIDE, GHAST_WIDE),
                (GHAST_AT, 0, GHAST_AT),
                window={face: GHAST_ART for face in FACES})
    return [body] + tentacles


DRIED_GHASTS = {"default": dried_ghast()}


# --- heavy cores ------------------------------------------------------------
#
# `heavy_core.png` is a 16x16 file holding three eight by eight pictures rather
# than one tile: the top with its rings at (0,0), the bottom beside it at (8,0),
# and the side under them at (0,8), which every one of the four walls wears. The
# block is the eight by eight by eight cube those pictures were drawn for.
#
# Faces left to work their own window out from where the cube sits read the
# middle of the file, which straddles all three pictures and the empty quarter
# under the bottom, so the core comes out as mismatched plates.
CORE_SIDE = 8
CORE_FACES = {"up": (0, 0), "down": (CORE_SIDE, 0)}

heavy_core = Cube(
    (CORE_SIDE, CORE_SIDE, CORE_SIDE),
    ((16 - CORE_SIDE) // 2, 0, (16 - CORE_SIDE) // 2),
    texture="@up",
    window={face: (CORE_FACES.get(face, (0, CORE_SIDE))
                   + (CORE_SIDE, CORE_SIDE))
            for face in FACES})

HEAVY_CORES = {"default": [heavy_core]}


# --- brewing stands ---------------------------------------------------------
#
# A brewing stand is a rod standing in a channel between three stone plates, not
# a rod standing on a slab. Drawn as one 14 by 14 plate it is a paving stone with
# a pole through it, and the pole sat on top of that plate rather than on the
# floor, so it stood two pixels proud of the block.
#
# `brewing_stand` draws the rod down the middle of its tile with the arms that
# hold the bottles either side of it, so a face taking the whole tile wears the
# arms as well. The rod names the two pixel column it wants.
#
# **The plates are placed from the sockets on the base tile.** Bedrock ships no
# model for this block and `brewing_stand_base` is opaque across the whole tile,
# so the only thing in the pack that says where one plate ends and the next
# begins is the three bottle sockets drawn on it, at (3.5, 3.5), (3.5, 11.5) and
# (12, 7.5). Each plate is the part of the tile its socket sits in the middle of.
BREW_ROD = "@up"            # brewing_stand
BREW_BASE = "@down"         # brewing_stand_base
ROD_WIDE, ROD_TALL = 2, 14
PLATE_TALL = 2


def brew_plate(size, at):
    """One of the three stone plates, reading its own part of the base tile."""
    wide, tall, deep = size
    x, _up, z = at
    return Cube(size, at, texture=BREW_BASE, window={
        "up": (x, z, wide, deep), "down": (x, z, wide, deep),
        "north": (x, 16 - tall, wide, tall),
        "south": (x, 16 - tall, wide, tall),
        "east": (z, 16 - tall, deep, tall),
        "west": (z, 16 - tall, deep, tall)})


brew_rod = Cube((ROD_WIDE, ROD_TALL, ROD_WIDE), (7, 0, 7), texture=BREW_ROD,
                window={
                    "north": (7, 1, ROD_WIDE, ROD_TALL),
                    "south": (7, 1, ROD_WIDE, ROD_TALL),
                    "east": (7, 1, ROD_WIDE, ROD_TALL),
                    "west": (7, 1, ROD_WIDE, ROD_TALL),
                    "up": (7, 7, ROD_WIDE, ROD_WIDE),
                    "down": (7, 7, ROD_WIDE, ROD_WIDE)})

BREWING_STANDS = {"default": [
    brew_rod,
    ## the whole of one side, and the other side halved. The channel between
    ## them is the two pixels the rod stands in.
    brew_plate((7, PLATE_TALL, 16), (9, 0, 0)),
    brew_plate((7, PLATE_TALL, 8), (0, 0, 0)),
    brew_plate((7, PLATE_TALL, 8), (0, 0, 8)),
]}


# --- flower pots ------------------------------------------------------------
#
# A flower pot is a hollow box, not a solid one: four terracotta walls a pixel
# thick with a plug of dirt sunk inside them, six across and six tall, standing
# in the middle of its block. Drawn as one cube of the compost tile, which is
# what the table said, it is a brown block with nothing pot-shaped about it.
#
# `flower_pot.png` is a tile with two pictures on it rather than one texture:
# the rim seen from above at (5,5), six across and six down with the hole in
# the middle of it, and the outside of the wall under it at (5,10). Each face
# reads the part of whichever of those it belongs to, so a wall a pixel wide
# takes a one pixel slice and not the whole picture squeezed into it.
POT = "@up"                 # flower_pot; the block declares one texture for all
POT_SIDE = (5, 10)          # the outside of the wall, on the tile
POT_RIM = (5, 5)            # the rim from above, with its hole
POT_AT = 5                  # where the pot stands in its block
POT_WIDE = 6
POT_TALL = 6
DIRT = "textures/blocks/dirt"
DIRT_DEEP = 4               # the soil sits below the rim, as vanilla draws it


def pot_wall(size, at):
    """One wall, reading its own slice of the tile's two pictures.

    Both pictures are the pot six across and six down, so a face's slice of one
    is where the wall sits within the pot: along x for the faces you look at
    from the front, along z for the ends, and the footprint for the rim.
    """
    wide, tall, deep = size
    x, y, z = (n - POT_AT for n in at)
    side_y = POT_SIDE[1] + POT_TALL - y - tall
    return Cube(size, at, texture=POT, window={
        "north": (POT_SIDE[0] + x, side_y, wide, tall),
        "south": (POT_SIDE[0] + x, side_y, wide, tall),
        "east": (POT_SIDE[0] + z, side_y, deep, tall),
        "west": (POT_SIDE[0] + z, side_y, deep, tall),
        "up": (POT_RIM[0] + x, POT_RIM[1] + z, wide, deep),
        "down": (POT_RIM[0] + x, POT_RIM[1] + z, wide, deep)})


FLOWER_POTS = {"default": [
    ## the two long walls, then the two short ones between them
    pot_wall((1, POT_TALL, POT_WIDE), (POT_AT, 0, POT_AT)),
    pot_wall((1, POT_TALL, POT_WIDE), (POT_AT + POT_WIDE - 1, 0, POT_AT)),
    pot_wall((POT_WIDE - 2, POT_TALL, 1), (POT_AT + 1, 0, POT_AT)),
    pot_wall((POT_WIDE - 2, POT_TALL, 1),
             (POT_AT + 1, 0, POT_AT + POT_WIDE - 1)),
    ## and the soil, at its own pixel scale rather than a whole tile shrunk
    Cube((POT_WIDE - 2, DIRT_DEEP, POT_WIDE - 2), (POT_AT + 1, 0, POT_AT + 1),
         texture=DIRT,
         window={face: (0, 0, POT_WIDE - 2, POT_WIDE - 2) for face in FACES}),
]}


# --- decorated pots ---------------------------------------------------------
#
# The body and the neck read two different pictures, and neither is a terrain
# tile. `decorated_pot_side` is the pot's wall, fourteen across and the height
# of the block, and `decorated_pot_base` is a 32x32 sheet holding the unwrap of
# the neck across the top of it and the body's top and bottom under that.
#
# Faces left to work their window out from where their cube sits read that
# sheet as if it were a tile, which lands the body's top on the neck's unwrap
# and on the empty row between the two, so the pot comes out with holes through
# it. Every face names the part of the sheet it wants.
POT_SHEET = 32
POT_BASE = "@up"                # decorated_pot_base, on up and down
POT_WALL = "@north"             # decorated_pot_side, on the four sides
BODY_WIDE = 14
BODY_TALL = 12
NECK_WIDE = 8
NECK_TALL = 4

## the neck's unwrap on the sheet, in the order Bedrock lays a box out: the two
## square faces along the top, then the four walls in a strip under them
NECK_FACES = {
    "up": (NECK_WIDE, 0, NECK_WIDE, NECK_WIDE),
    "down": (NECK_WIDE * 2, 0, NECK_WIDE, NECK_WIDE),
    "west": (0, NECK_WIDE, NECK_WIDE, NECK_TALL),
    "south": (NECK_WIDE, NECK_WIDE, NECK_WIDE, NECK_TALL),
    "east": (NECK_WIDE * 2, NECK_WIDE, NECK_WIDE, NECK_TALL),
    "north": (NECK_WIDE * 3, NECK_WIDE, NECK_WIDE, NECK_TALL),
}
## and the body's two square faces, side by side under the neck's strip
BODY_FACES = {
    "up": (0, 13, BODY_WIDE, BODY_WIDE),
    "down": (BODY_WIDE, 13, BODY_WIDE, BODY_WIDE),
}


def on_sheet(name, region, sheet=POT_SHEET):
    """A texture reference and a window for one region of an entity sheet.

    Only a 16x16 window of a texture becomes a tile, so the reference carries
    the corner that tile starts at and the window is measured from there. The
    corner is pulled back far enough that the region fits inside the tile and
    never past the edge of the sheet, which is why the last face of a strip
    still reads from a corner sixteen in.
    """
    x, y, wide, tall = region
    at = [max(0, min(n, sheet - 16)) for n in (x, y)]
    return ("%s#%d,%d" % (name, at[0], at[1]),
            (x - at[0], y - at[1], wide, tall))


def sheet_cube(size, at, faces, name):
    """A cube whose every face names its own region of one sheet."""
    texture, window = {}, {}
    for face, region in faces.items():
        texture[face], window[face] = on_sheet(name, region)
    return Cube(size, at, texture=texture, window=window)


def pot_body():
    """The pot's wall, its shoulder and its floor.

    The wall texture is the height of the block and the body is the lower three
    quarters of it, so the wall reads the bottom twelve rows: the top four
    belong to the neck, which takes its own from the sheet.
    """
    texture, window = {}, {}
    for face in ("north", "south", "east", "west"):
        texture[face] = POT_WALL
        window[face] = (1, 16 - BODY_TALL, BODY_WIDE, BODY_TALL)
    for face, region in BODY_FACES.items():
        texture[face], window[face] = on_sheet(POT_BASE, region)
    return Cube((BODY_WIDE, BODY_TALL, BODY_WIDE), (1, 0, 1),
                texture=texture, window=window)


DECORATED_POTS = {"default": [
    pot_body(),
    sheet_cube((NECK_WIDE, NECK_TALL, NECK_WIDE),
               ((16 - NECK_WIDE) // 2, BODY_TALL, (16 - NECK_WIDE) // 2),
               NECK_FACES, POT_BASE),
]}


def main():
    print("writing the mounted forms")
    write("hanging_sign", HANGING_SIGNS)
    write("bell", BELLS)
    ## the grindstone turns about the wheel's own height rather than the middle
    ## of the block, which is where its entry has always put the pivot
    write("grindstone", GRINDSTONES, center=(8, 7.04, 8))
    write("campfire", CAMPFIRES, center=(8, 4, 8))
    write("shelf", SHELVES)
    write("door", DOORS)
    write("tripwire_hook", TRIPWIRE_HOOKS)
    write("sculk_shrieker", SHRIEKERS)
    write("tripwire", STRINGS)
    write("flower_pot", FLOWER_POTS)
    write("decorated_pot", DECORATED_POTS)
    ## the rod turns about the middle of the block, not the middle of the base
    write("brewing_stand", BREWING_STANDS, center=(8, 6.4, 8))
    write("heavy_core", HEAVY_CORES, center=(8, 4, 8))
    write("dried_ghast", DRIED_GHASTS)
    ## a shrieker was drawn from the plain cube family, so it needs pointing at
    ## the one written here; `tripwire` already has both of its block ids
    define(["sculk_shrieker"], "sculk_shrieker")


if __name__ == "__main__":
    main()

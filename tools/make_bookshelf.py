"""Generate the chiseled bookshelf's sixty-four filled states.

    python tools/make_bookshelf.py

A chiseled bookshelf has six slots and remembers which of them hold a book, in a
`books_stored` state that is a six bit number, so there are sixty-four ways it
can look. Vanilla draws the shelf itself from `chiseled_bookshelf_empty` and lays
`chiseled_bookshelf_occupied` over the slots that are filled, and that is what
this builds: one variant per value, the shelf plus a small panel over each
occupied slot.

The slot grid is measured from the two textures rather than guessed, because the
pixels where they differ are exactly the six book faces. It comes out as three
columns four pixels wide at x 1, 6 and 11, and two rows six pixels tall at y 1
and 9.

`blocks.json` names the front texture `chiseled_bookshelf_front`, which no
vanilla pack ships and `terrain_texture.json` has no entry for, so that name
resolves to nothing. Every variant here names its own front texture instead.

Writes into `lookups/block_shapes.json` and `lookups/block_uv.json`; nothing here
is needed at run time.
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
FAMILY = "chiseled_bookshelf"

EMPTY = "textures/blocks/chiseled_bookshelf_empty"
OCCUPIED = "textures/blocks/chiseled_bookshelf_occupied"

## the slot grid, in texture pixels, measured from where the two textures differ
COLUMNS = (1, 6, 11)
ROWS = (1, 9)
SLOT_WIDE = 4
SLOT_TALL = 6

## how far a book panel stands proud of the shelf front, so the two faces do not
## fight over the same plane
PROUD = 0.02

BODY = 0.95


def slot_box(index):
    """One slot, as a texture window and as a box on the front of the block.

    The front face is the north one, which faces away along z, so a slot's
    texture column is its position along x and its texture row counts down from
    the top of the block.
    """
    column = COLUMNS[index % 3]
    row = ROWS[index // 3]
    u, v = column / 16.0, row / 16.0
    wide, tall = SLOT_WIDE / 16.0, SLOT_TALL / 16.0
    ## v counts down from the top of the tile; y counts up from the floor
    x, y = u, 1.0 - (v + tall)
    return (u, v, wide, tall), (x, y)


def variant(mask):
    """The shape and the texture windows for one arrangement of books."""
    filled = [i for i in range(6) if mask & (1 << i)]

    sizes = [[BODY, BODY, BODY]]
    offsets = [[0, 0, 0]]
    windows = {face: [[1, 1]] for face in FACES}
    origins = {face: [[0, 0]] for face in FACES}
    ## the shelf's own front, which is where the empty slots are drawn
    front = [EMPTY]

    for index in filled:
        (u, v, wide, tall), (x, y) = slot_box(index)
        sizes.append([wide, tall, PROUD])
        offsets.append([x, y, -PROUD])
        for face in FACES:
            ## only the north face of a panel is really seen; the slivers round
            ## its edge take the same window rather than a meaningless one
            windows[face].append([wide, tall])
            origins[face].append([u, v])
        front.append(OCCUPIED)

    shape = {
        "size": sizes,
        "offsets": offsets,
        "center": [BODY / 2, BODY / 2, BODY / 2],
    }
    uv = {
        "uv_sizes": windows,
        "offset": origins,
        ## the shelf front and every panel name their texture outright: the one
        ## blocks.json names for this face does not exist in any vanilla pack
        "overwrite": {"north": front},
    }
    return shape, uv


def main():
    shapes = {}
    uvs = {}
    for mask in range(64):
        shape, uv = variant(mask)
        shapes[str(mask)] = shape
        uvs[str(mask)] = uv

    ## an empty shelf is what one looks like before anything is put in it
    shapes["default"] = shapes["0"]
    uvs["default"] = uvs["0"]

    print("shapes: %s" % lookup_writer.put(SHAPES, FAMILY, shapes))
    print("uv    : %s" % lookup_writer.put(UV, FAMILY, uvs, tight=True))

    total = sum(len(shapes[k]["size"]) for k in shapes)
    print("%d variants, %d cubes across the table" % (len(shapes), total))
    for name in (SHAPES, UV):
        json.loads(io.open(name, encoding="utf-8").read())
    print("both tables still parse")


if __name__ == "__main__":
    main()

"""Put the right texture on each part of the blocks built from several cubes.

    python tools/fix_problem_blocks.py

A block made of one cube can take the six textures Bedrock declares for it and be
right. A block made of several cannot: every cube gets the same six, so a
grindstone's legs are painted with the wheel's texture on top and a beacon's
glass shell, its core and its obsidian base are all painted alike.

`block_uv.json` has an `overwrite` list for exactly this, a texture per cube per
face, and the families here are the ones that need one. A value written `@up` or
`@down` means
"whatever this block declares for that face", so one entry serves every wood a
sign comes in and every state a campfire has, without naming a single texture
file.

Nothing here is needed at run time; it edits the lookup tables in place.
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


def load(path):
    return json.load(io.open(path, encoding="utf-8"))


def all_faces(per_cube):
    """The same list of textures on every face of the block."""
    return {face: list(per_cube) for face in FACES}


def main():
    shapes = load(SHAPES)
    uv = load(UV)
    changed = []

    def revise(family, variant, overwrite, from_variant="default"):
        entry = json.loads(json.dumps(uv[family][from_variant]))
        entry["overwrite"] = overwrite
        uv[family][variant] = entry

    ## --- beacon: obsidian base, the beacon itself, then the glass shell -----
    ## Bedrock declares beacon_base as obsidian, beacon_shell as glass and
    ## beacon_core as the beacon texture, on down, side and up. Without an
    ## overwrite all three cubes take all three and the shell is not glass.
    revise("beacon", "default", all_faces(["@down", "@up", "@north"]))
    changed.append("beacon")

    ## --- bell: the bell, its crown, and the beam it hangs from --------------
    ## the beam is the wood the block declares on its east face; the crown is
    ## the bell top
    revise("bell", "default", all_faces(["default", "@up", "@east"]))
    changed.append("bell")

    ## --- grindstone: two legs, two pivots, the wheel ------------------------
    ## the legs are the log the block declares on down, the pivots the texture
    ## it declares on north, and only the wheel keeps the block's own faces
    revise("grindstone", "default",
           all_faces(["@down", "@down", "@north", "@north", "default"]))
    changed.append("grindstone")

    ## --- campfire: four logs, lit or out ------------------------------------
    ## A campfire declares its lit logs on the side faces and its dead ones on
    ## down, so the two states are the same four cubes wearing different
    ## textures. The soul campfire is the same family and gets its own lit
    ## texture from the same reference.
    revise("campfire", "0", all_faces(["@north"] * 4))       # burning
    revise("campfire", "1", all_faces(["@down"] * 4))        # extinguished
    revise("campfire", "default", all_faces(["@north"] * 4))
    for variant in ("0", "1"):
        shapes["campfire"][variant] = shapes["campfire"]["default"]
    changed.append("campfire")

    ## --- tripwire hook: the plate, the hook, the wire -----------------------
    revise("tripwire_hook", "default",
           all_faces(["@down", "@north", "@east"]))
    changed.append("tripwire_hook")

    ## --- the two block tall flowers -----------------------------------------
    ## Bedrock declares the upper half on up, the lower on down, and something
    ## else entirely on side. For a lilac the side texture is the *sunflower's*
    ## back, so both halves have to be pinned to up and down instead.
    revise("double_plant", "default", all_faces(["@down", "@down"]))
    revise("double_plant", "top", all_faces(["@up", "@up"]),
           from_variant="top")
    changed.append("double_plant")

    for family in sorted(set(changed)):
        lookup_writer.put(UV, family, uv[family], tight=True)
        if family in ("campfire",):
            lookup_writer.put(SHAPES, family, shapes[family])

    print("gave %d families a texture per cube:" % len(set(changed)))
    for family in sorted(set(changed)):
        print("   %s" % family)
    for path in (SHAPES, UV):
        json.loads(io.open(path, encoding="utf-8").read())
    print("both tables still parse")


if __name__ == "__main__":
    main()

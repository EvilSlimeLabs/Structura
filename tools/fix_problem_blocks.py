"""Put the right texture on each part of the blocks built from several cubes.

    python tools/fix_problem_blocks.py

A block made of one cube can take the six textures Bedrock declares for it and
be right. A block made of several cannot, because every cube gets the same six,
so a beacon's glass shell, its core and its obsidian base are all painted alike.

`block_uv.json` has an `overwrite` list for exactly this, a texture per cube per
face. A value written `@up` or `@down` means "whatever this block declares for
that face", so one entry serves every wood a block comes in and every state it
has, without naming a single texture file.

The families whose forms differ by how they are mounted are written by
`tools/make_block_forms.py` instead, which owns their shapes as well as their
textures. Nothing here is needed at run time; it edits the lookup tables in
place.
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

    print("gave %d families a texture per cube:" % len(set(changed)))
    for family in sorted(set(changed)):
        print("   %s" % family)
    for path in (SHAPES, UV):
        json.loads(io.open(path, encoding="utf-8").read())
    print("both tables still parse")


if __name__ == "__main__":
    main()

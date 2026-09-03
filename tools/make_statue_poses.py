"""Give the copper golem statue a shape for each pose it can be placed in.

    python tools/make_statue_poses.py

A copper golem statue does not record its pose in a block state. It keeps it in
the block entity beside the block, the way a sign keeps its text, so a structure
holding four statues in four poses has a single palette entry for all of them and
the pose has to be read from `block_position_data`. `structure_reader` reads that
now and `structura_core` turns the `Pose` field into the shape variant, which is
what this table answers.

The four poses are built from the same three pieces, a base, a body and a head,
moved and leaned rather than remodelled, so the UV windows the default already
maps into the golem's texture sheet stay valid for all of them. What the poses
actually look like in game is not knowable from here; these are distinguishable
and upright, and want checking against a real world.

Writes into `lookups/block_shapes.json`. Not needed at run time.
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
FAMILY = "copper_golem_statue"

## base, body, head: the sizes the default already uses
SIZES = [[0.5, 0.125, 0.375], [0.375, 0.4375, 0.3125], [0.5, 0.375, 0.4375]]

## Where each piece sits, per pose, and how far the body and head lean.
## 0 standing, 1 sitting, 2 running, 3 arms raised, which is the order the game
## numbers them in.
POSES = {
    "0": {"offsets": [[0.25, 0, 0.3125],
                      [0.3125, 0.125, 0.34375],
                      [0.25, 0.5625, 0.28125]],
          "rotation": [[0, 0, 0], [0, 0, 0], [0, 0, 0]]},

    ## sitting: everything drops, and the head tips back a little
    "1": {"offsets": [[0.25, 0, 0.3125],
                      [0.3125, 0.0625, 0.34375],
                      [0.25, 0.4375, 0.28125]],
          "rotation": [[0, 0, 0], [0, 0, 0], [-10, 0, 0]]},

    ## running: the body pitches forward and the head follows it
    "2": {"offsets": [[0.25, 0, 0.28125],
                      [0.3125, 0.125, 0.3125],
                      [0.25, 0.53125, 0.21875]],
          "rotation": [[0, 0, 0], [-18, 0, 0], [-18, 0, 0]]},

    ## reaching up: the body stretches and the head lifts with it
    "3": {"offsets": [[0.25, 0, 0.3125],
                      [0.3125, 0.1875, 0.34375],
                      [0.25, 0.625, 0.28125]],
          "rotation": [[0, 0, 0], [0, 0, 0], [12, 0, 0]]},
}


def main():
    shapes = json.load(io.open(SHAPES, encoding="utf-8"))
    uv = json.load(io.open(UV, encoding="utf-8"))

    built = {}
    for pose, body in sorted(POSES.items()):
        built[pose] = {
            "size": [list(size) for size in SIZES],
            "offsets": [list(offset) for offset in body["offsets"]],
            "rotation": [list(turn) for turn in body["rotation"]],
            "center": [0.5, 0.47, 0.5],
        }
    ## a statue placed with no entity data at all is standing
    built["default"] = built["0"]

    ## every pose is the same three cubes, so one set of texture windows serves
    ## all of them
    windows = uv[FAMILY]["default"]
    for pose in built:
        uv[FAMILY][pose] = windows

    print("shapes: %s" % lookup_writer.put(SHAPES, FAMILY, built))
    print("uv    : %s" % lookup_writer.put(UV, FAMILY, uv[FAMILY], tight=True))
    print("%d poses" % len(POSES))

    for path in (SHAPES, UV):
        json.loads(io.open(path, encoding="utf-8").read())
    print("both tables still parse")


if __name__ == "__main__":
    main()

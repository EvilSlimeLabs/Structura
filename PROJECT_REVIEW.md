# Project review

The crash, wrong-output, robustness and structure findings from the original
pass have all been worked. What is left is here: the parts that could not be
settled from this side of the screen, and the checks that would settle them.

Block coverage is a separate list — see `BLOCK_COVERAGE_GAPS.md`.

---

## Needs a live world to settle

Everything in this section is a change that was reasoned out from cube geometry
and vanilla's own model files. The arithmetic can be checked here; how it looks
cannot. None of it has been seen in game.

**The horizontal UV window is still wrong for cubes narrower than their block.**
Vertical windows are now correct everywhere — a half-height cube takes half a
texture tile. The horizontal axis was deliberately left alone, because setting
it needs to know which way U runs across the east and west faces, and there is
no worked example anywhere in `block_uv.json` to copy: every existing entry is
either full width or a symmetric inset. Two shapes are affected.

- `stairs`, both variants, cube index 1. The step is half a block deep, so its
  east and west faces are half as wide as the tile they are given.
- `trapdoor`, the `open` variant. Its east and west faces are 3 pixels wide and
  currently take a full tile; the `uv_sizes` entry for those faces also has the
  two axes the wrong way round, `[1, 0.1875]` where the face is 0.1875 wide and
  a full block tall.

**The check:** place an oak stair against an oak plank wall, and an open oak
trapdoor beside a plank block, and look at the narrow side faces. If the plank
lines run at the right scale and line up with the block next to them, the
current full-width window is fine and only `uv_sizes` needs the swap. If they
are stretched, those faces need a half-tile window, and the direction it runs is
whatever makes the grain continue.

**The vertical UV fixes want confirming.** Slabs, stairs, trapdoors and snow
layers all changed. The fastest single check: build a pack containing a bottom
slab, a top slab, a bottom stair, a top stair, a closed trapdoor and snow at
several depths, all in oak or another plank, next to full plank blocks. Every
one of them should have its grain continuous with the block beside it. A texture
that looks vertically squashed, or offset by a few pixels, means that shape's
window is wrong.

**Snow at height 7 now renders as a full block.** It previously fell back to the
thinnest layer, because `block_shapes.json` only described heights 0 to 6.
Bedrock stores `height` 0–7 as 2 to 16 pixels, so 7 is a full cube. Worth
looking at once, next to a snow block.

---

## Cannot be exercised here

**`updater.py`** needs the update server, which this fork does not publish to.
The extraction filter is checked against a hand-built archive containing path
escapes, an absolute path and a program file, and rejects all of them, but a
real update has not been run through it. It permits both `lookups/` and
`Vanilla_Resource_Pack/`, because that is what `build.py --update-package`
produces — narrowing it to `lookups/` alone would quietly break updates.

# Block coverage

Blocks that `CommunityVanillaResourcePack` defines and
`lookups/block_definition.json` does not. A block missing from that file raises
a `KeyError` in `armorstandgeo.make_block`, which `structura._add_blocks_to_geo`
catches and records as an unsupported block — so the block is silently dropped
from the ghost model and the user only sees it in the skipped list.

**The gap is closed.** All 158 blocks that were uncovered against
`CommunityVanillaResourcePack` at `b6bdfc8` (min engine 1.26.40) are now
defined, and every block in `test_structures/` builds. What is left below is the
record of what was decided and the handful of shapes that are approximations.

Check either number at any time:

```bash
python tools/audit_blocks.py --gaps        blocks the community pack has and we do not
python tools/coverage_report.py            what the bundled structures still drop
```

---

## Where it stands

| Check | Result |
| --- | --- |
| Blocks declared in `block_definition.json` | 1380 (1335 drawn, 45 `ignore`) |
| Declared blocks whose textures do not resolve | 0 |
| Community pack blocks with no definition | 0 |
| Blocks skipped across the 108 bundled structures | 0 |

The 130 blocks the audit reports as *expected unresolved* are Education Edition
and unobtainable blocks that no vanilla pack ships textures for. They are
declared so a structure containing one is named rather than mysterious, and they
will never resolve.

---

## What was added

**62 needed only a definition line.** The bundled pack already carried their
`blocks.json` entry and textures.

- **Legacy stone slab ids (12)** — `stone_slab` through `stone_slab4` and their
  `double_` forms, plus `petrified_oak_slab`, `petrified_oak_double_slab`,
  `pale_oak_double_slab`, `bamboo_mosaic_double_slab`. Slabs map to `slab`,
  double slabs to `cube`. The numbered variants pick their material through
  `stone_slab_type_2/3/4`, which `variants.json` already defined. `stone_slab`
  alone appeared in ten of the bundled structures, including the ones used to
  check slab orientation.
- **camelCase and pre-flattening spellings (10)** — `carpet`, `concretePowder`,
  `seaLantern`, `yellow_shulker_box`, `chiseled_stone_bricks`,
  `cracked_stone_bricks`, `quartz_pillar` (`tree`, so `pillar_axis` turns it),
  `deprecated_anvil`, `deprecated_purpur_block_1` and `_2`.
- **Two-tall plants (7)** — `large_fern`, `lilac`, `peony`, `pitcher_plant`,
  `rose_bush`, `sunflower`, `tall_grass`, all `double_plant`.
- **Single-height flora and the pale garden (6)** — `lily_of_the_valley`,
  `open_eyeblossom`, `closed_eyeblossom` and `pale_hanging_moss` as
  `cross_texture`, `pale_oak_door` as `door`, and `resin_clump` as `vine-multi`,
  which is what `glow_lichen` and `sculk_vein` use — it is a multi-face decal
  driven by `multi_face_direction_bits`, not a cross.
- **Chiseled copper (8)** — all four oxidation stages and their waxed forms,
  `cube`.
- **Light block levels (16)** — `light_block_0` through `light_block_15`,
  `ignore`. They are invisible in game, as the plain `light_block` already was.
- **1.21 odds and ends (3)** — `vault` as `cube`, `piglin_head` as `ignore` to
  match every other head, and `heavy_core` on a new shape.

**96 needed assets**, pulled from the submodule with
`tools/sync_vanilla_pack.py --add-block` — 95 `blocks.json` entries, 64
`terrain_texture.json` entries and 92 texture files.

- **Sulfur and cinnabar (34)** — two full stone families: block, bricks,
  polished and (sulfur) chiseled and potent forms, each with slab, double slab,
  stairs and wall. Plus `sulfur_spike` on a new shape.
- **Copper, in all eight oxidation and waxing states (32)** — bars as `pane`,
  chests as `chest`, lanterns as `lantern`, statues on a new shape.
- **Lightning rod oxidation (7)** — the seven oxidised and waxed forms of a
  block whose plain id was already covered.
- **Shelves (12)** — one per wood, on a new shape.
- **New flora (8)** — `bush`, `cactus_flower`, `firefly_bush`,
  `golden_dandelion`, `short_dry_grass`, `tall_dry_grass` and `wildflowers` as
  `cross_texture`; `leaf_litter` as `carpet`, because it lies on the floor
  rather than standing up as a cross.
- **The rest (3)** — `creaking_heart` as `tree` so `pillar_axis` turns it,
  `copper_torch` as `torch`, `dried_ghast` as `cube`.

---

## Two defects the work surfaced

**`soul_campfire` was mapped to `cube`.** It is a campfire, and `campfire` has
no rotation table, so the mismapping only mattered because of the second defect.

**A rotation state the table could not describe dropped the block.**
`make_block` indexed `block_rotation.json` directly, so a `cube` carrying
`direction` 0 — a state the `cube` entry never listed — raised a `KeyError` and
the block was recorded as unsupported. It now leaves the block unrotated
instead. Losing an orientation is a smaller wrong answer than losing the block,
and it matches how the shape-variant lookup beside it already behaved. This was
the only block still being dropped by the bundled structures.

---

## Shapes that are approximations

These four have geometry no existing entry described, and nothing in the
textures or the lookup tables pins their real dimensions down. They are drawn
close enough to be useful as placement guides and are **worth a look in a live
world** before anyone trusts the exact sizes.

| Family | What it draws | What is uncertain |
| --- | --- | --- |
| `heavy_core` | a half-size cube floating at the middle of the block | the exact edge length |
| `shelf` | a board across the full width, 3/16 tall and half a block deep, mounted at mid height and turned by facing | the height it sits at and its depth |
| `sulfur_spike` | three boxes narrowing toward the tip | `blocks.json` hands this block five *part* textures through the six face slots — frustum, base, tip, middle, merge — rather than one texture per face, so the parts wear them in face order. The silhouette is right; which part shows which texture is not |
| `copper_golem_statue` | a full-height box narrower than a block | the footprint. It wears the plain copper block texture, so only the proportions are in question |

`vault` is drawn as a plain cube. It is close to block-sized, so this is a
smaller compromise than the four above, but it is not exact either.

---

## Two orphans in the tables

`block_shapes.json` defines `waterlily` and `block_uv.json` defines
`purpur_block`, and no block maps to either — `waterlily` the block uses
`lilypad`, and `purpur_block` uses `tree`. Neither is reachable, so neither is
breaking anything; they are dead entries that only show up if you compare the
two files directly. Left alone rather than deleted, since removing table data
that nothing reads is churn without a reader.

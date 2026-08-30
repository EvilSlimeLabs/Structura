# Block coverage gaps

Blocks that the `CommunityVanillaResourcePack` submodule defines and
`lookups/block_definition.json` does not. A block missing from that file raises
a `KeyError` in `armorstandgeo.make_block`, which `structura._add_blocks_to_geo`
catches and records as an unsupported block — so the block is silently dropped
from the ghost model and the user only sees it in the skipped list.

Generated against `CommunityVanillaResourcePack` at `b6bdfc8` (min engine
1.26.40) versus `block_definition.json` at 1223 entries. **158 blocks are
uncovered.** Nothing in this file has been acted on.

## How to read the tables

Three separate things can be missing, and they cost very different amounts of
work:

- **definition** — a line in `lookups/block_definition.json` mapping the block
  to a shape family. Every entry below needs this.
- **blocks.json** — an entry in `Vanilla_Resource_Pack/blocks.json` mapping the
  block to texture short names. 95 of the 158 need one.
- **textures** — terrain_texture.json entries plus the `.png` files. 88 of the
  158 need these; they can be copied from the submodule.

62 of the 158 need **only** the definition line — the bundled pack already
carries their blocks.json entry and textures. Those are the cheap ones.

A spot check ran `make_block` against 30 of the definition-only candidates with
a hand-supplied shape family; all 30 produced geometry without error, so for
that group a single line really is the whole fix.

---

## Priority 1 — uncovered blocks that appear in the bundled test structures

These are being dropped today, from structures that ship with the repo. All of
them are definition-only fixes.

| Block | Suggested shape | Appears in |
| --- | --- | --- |
| `stone_slab` | `slab` | 10 palettes |
| `pale_oak_door` | `door` | 4 palettes |
| `double_stone_slab` | `cube` | 3 palettes |
| `chiseled_copper` | `cube` | 1 palette |
| `exposed_chiseled_copper` | `cube` | 1 palette |
| `weathered_chiseled_copper` | `cube` | 1 palette |
| `oxidized_chiseled_copper` | `cube` | 1 palette |
| `large_fern` | `double_plant` | 1 palette |
| `lilac` | `double_plant` | 1 palette |
| `peony` | `double_plant` | 1 palette |
| `rose_bush` | `double_plant` | 1 palette |
| `sunflower` | `double_plant` | 1 palette |
| `tall_grass` | `double_plant` | 1 palette |
| `pitcher_plant` | `double_plant` | 1 palette |

`stone_slab` and `double_stone_slab` matter most. They are the pre-flattening
ids that older worlds still store, they carry `stone_slab_type` (already in
`lookups/variants.json`) and `top_slot_bit`, and they turn up in ten of the
bundled structures — including the ones used to check slab orientation.

---

## Priority 2 — definition-only, no new assets

The bundled pack already has everything these need.

**Legacy stone slab ids (12)** — `stone_slab`, `stone_slab2`, `stone_slab3`,
`stone_slab4`, `double_stone_slab`, `double_stone_slab2`, `double_stone_slab3`,
`double_stone_slab4`, `petrified_oak_slab`, `petrified_oak_double_slab`,
`pale_oak_double_slab`, `bamboo_mosaic_double_slab`.
Slabs map to `slab`, double slabs to `cube`. The numbered variants select their
material through `stone_slab_type_2/3/4`, all of which `variants.json` already
defines.

**Other legacy or aliased ids (10)** — `carpet`, `concretePowder`, `seaLantern`,
`yellow_shulker_box`, `chiseled_stone_bricks`, `cracked_stone_bricks`,
`quartz_pillar`, `deprecated_anvil`, `deprecated_purpur_block_1`,
`deprecated_purpur_block_2`.
The pack already covers the flattened spellings (`concrete_powder`,
`sea_lantern`, `stonebrick`); these are the camelCase and pre-flattening names
the same blocks are stored under in older structures. `quartz_pillar` wants
`tree` so `pillar_axis` rotates it.

**Double plants (8)** — `large_fern`, `lilac`, `lily_of_the_valley`, `peony`,
`pitcher_plant`, `rose_bush`, `sunflower`, `tall_grass`.
All `double_plant`. These are the flattened replacements for the `double_plant`
block that the pack covers through the old `flower_type` variant.

**Chiseled copper (8)** — `chiseled_copper` and its exposed / weathered /
oxidized / waxed forms. All `cube`.

**Pale garden, 1.21.4 (5)** — `pale_oak_door` (`door`), `open_eyeblossom` and
`closed_eyeblossom` (`cross_texture`), `pale_hanging_moss` (`cross_texture`),
`resin_clump` (`cross_texture`).

**Misc 1.21 (3)** — `vault`, `heavy_core`, `piglin_head`. `vault` and
`heavy_core` are not cubes in game; `cube` is a rough stand-in and the shape is
worth a second look. `piglin_head` is a skull, and `skull` is currently mapped
to `ignore` — decide whether heads should render at all before adding it.

**Light block levels (16)** — `light_block_0` through `light_block_15`. These
are invisible in game. They should almost certainly map to `ignore`, and the
existing `light_block` entry (currently `cube`, and broken because its
blocks.json entry has no `textures` field) should probably become `ignore` too.

---

## Priority 3 — new content, needs textures copied from the submodule

Each of these needs a definition line, a `blocks.json` entry, terrain_texture
entries and the `.png` files. The texture count is the number of distinct new
files the submodule would supply.

| Family | Blocks | New textures | Notes |
| --- | --- | --- | --- |
| Sulfur (Copper Age) | 18 | 15 | Full stone-family set plus `sulfur_spike`, which is a five-part multi-shape and needs a new shape entry |
| Cinnabar (Copper Age) | 16 | 4 | Full stone-family set; block, bricks, polished, chiseled, each with slab / stairs / wall / double slab |
| Shelves | 12 | 12 | One per wood type. New shape family — a shelf is a wall-mounted partial block with a facing direction |
| Copper bars | 8 | 4 | Reuses the `pane` shape; waxed forms share the unwaxed textures |
| Copper chests | 8 | 12 | `chest` shape already exists |
| Copper lanterns | 8 | 4 | `lantern` shape already exists |
| Copper golem statues | 8 | 0 | Textures already resolve; needs `blocks.json` entries. The statue is an entity-shaped model, so `cube` will look wrong — a new shape is the honest fix |
| Lightning rod oxidation | 7 | 4 | `lightning_rod` shape already exists |
| New flora | 8 | 10 | `bush`, `cactus_flower`, `firefly_bush`, `golden_dandelion`, `leaf_litter`, `short_dry_grass`, `tall_dry_grass`, `wildflowers`. Most are `cross_texture`; `leaf_litter` is a floor decal closer to `carpet` |
| Other new | 3 | 27 | `creaking_heart` (`tree`, `pillar_axis`), `copper_torch` (`torch`), `dried_ghast` (four hydration states, 24 textures) |

---

## Things to settle before working the list

- **Which shape family gets the benefit of the doubt.** `vault`, `heavy_core`,
  `copper_golem_statue`, `dried_ghast` and `sulfur_spike` all have geometry no
  existing entry in `block_shapes.json` describes. Mapping them to `cube` gets
  them on screen at the wrong size; leaving them out keeps them in the skipped
  list where the user at least sees the name. Neither is obviously right.
- **Whether the waxed variants deserve their own entries.** They are visually
  identical to the unwaxed block and quadruple the diff. They do need their own
  entries, because the lookup is by exact block id.
- **Whether `light_block_*` and `piglin_head` should be `ignore`.** That is a
  product call, not a lookup-table call.
- **Whether `Vanilla_Resource_Pack` should keep being hand-merged at all.**
  Every entry above is a manual copy out of the submodule. A script that merges
  the submodule's `blocks.json` and `terrain_texture.json` entries for a named
  list of blocks, and copies the textures they resolve to, would make this list
  and the next one much cheaper to work through. See `PROJECT_REVIEW.md`.

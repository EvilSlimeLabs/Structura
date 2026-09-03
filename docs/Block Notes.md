# Block notes

What to know before adding a block, changing how one looks, or working out why
one looks wrong. The tables themselves are described in `docs/Editing Blocks.md`;
this is the accumulated knowledge that is not obvious from reading them.

Coverage is closed and stays closed — check it at any time:

```bash
python tools/audit_blocks.py         every declared block resolved to a texture
python tools/coverage_report.py      what the bundled structures drop
```

Both should report nothing missing. `coverage_report.py` drives the real
pipeline against all 108 bundled structures, so it is the fastest way to see
whether a lookup change broke something.

---

## How a block becomes geometry

1. `lookups/block_definition.json` maps the block id to a **shape family**. No
   entry means the block is skipped and reported, not drawn.
2. `lookups/nbt_defs.json` says what each of the block's **states** means.
3. `structura.core._process_block` turns those states into a rotation, a
   texture variant, a shape variant and a few flags.
4. `armor_stand_geo_class.make_block` reads `block_shapes.json` and
   `block_uv.json` with the resulting variant name and emits cubes.

**`block_shapes.json` and `block_uv.json` must agree.** A variant in one and not
the other silently falls back to `default`, which is how a half-height cube ends
up wearing a full-height texture. Add variants to both.

---

## What a state can mean

`nbt_defs.json` maps a state name to one of these:

| Meaning | Effect | Example |
| --- | --- | --- |
| `rot` | picks a rotation from `block_rotation.json` | `minecraft:cardinal_direction` |
| `variant` | picks an index into a texture **list** via `variants.json` | `rehydration_level` |
| `top` | selects the `top` shape variant | `upper_block_bit` |
| `open_bit`, `hinge` | door and trapdoor flags | `open_bit` |
| `data` | the state's number names the shape variant | `books_stored` |
| `shape` | the state's **value** names the shape variant | `attachment` |

`data` and `shape` both end up as the variant name. `data` is for numbers,
`shape` for words — an `int()` on `"hanging"` raises. When a block carries
several `shape` states they are joined with `-` **in the order the state names
sort**, so `attached_bit` before `hanging` gives `"0-1"`. Write the variants in
that order or they will never be found.

A state that is not in `nbt_defs.json` is ignored entirely. That is the usual
reason a block looks the same however it is placed.

---

## Rotation tables need every form of the value

Bedrock gives some blocks a numeric `direction` and others a
`minecraft:cardinal_direction` **string**, and a few blocks carry both across
versions. `block_rotation.json` is a plain lookup: a value it has no key for is
drawn **unrotated, silently**.

That is what made every door face the same way — `door` had `0`–`3` and the
structures were giving it `"east"`. Twelve families had the same gap.

The numbering is not the same for every block:

- most blocks: `0` south, `1` west, `2` north, `3` east
- **doors**: `0` east, `1` south, `2` west, `3` north
- **trapdoors**: `0` east, `1` west, `2` south, `3` north
- **standing and hanging signs**: sixteen steps of 22.5°, not four

When adding a family, give it both the numbers and the words.

**Which way "facing 0" actually points is not knowable from here.** The tables
follow the convention every existing entry uses; confirm a new one in a world.

---

## One texture per cube, not per block

Bedrock declares six textures for a block — up, down and the four sides. A block
built from one cube can use them directly. A block built from several **cannot**:
without help, every cube gets the same six, so a grindstone's legs are painted
with the wheel's texture on top and a beacon's glass shell, its core and its
obsidian base are all painted alike.

`block_uv.json` has an `overwrite` entry for this: a texture per cube, per face.

```json
"overwrite": {"up": ["@down", "@up", "@north"], ...}
```

- a literal path is used as given
- `"default"` leaves that cube's face alone
- `"@up"`, `"@down"`, `"@north"` … mean **whatever this block declares for that
  face**, which is how one entry serves every wood a sign comes in and every
  state a campfire has without naming a single texture file

Prefer the `@` form. It survives a block gaining new variants and works for
families shared by many block ids.

---

## Textures that are not what they seem

- **Some are lists.** `terrain_texture.json` may map one name to several files —
  `dried_ghast_front` is four, one per drying stage. The `variant` mechanism
  indexes them through `variants.json`. A numeric state arrives from nbtlib as
  `Int(0)`, whose `str()` is `"Int(0)"` and not `"0"`; the lookup converts.
- **Some are flipbooks.** `campfire.png` is 16×128 — eight stacked frames — and
  `campfire_log_lit.png` is 16×64. Using one whole stretches every frame over the
  face; the UV window has to take one frame's worth of `v`.
- **Some are named and do not exist.** `blocks.json` names
  `chiseled_bookshelf_front`, which no vanilla pack ships and
  `terrain_texture.json` has no entry for. Name the real texture in `overwrite`.
- **Some are entity sheets.** `copper_golem.png` is 64×64 and `oak_hanging_sign.png`
  is 64×32 — atlases laid out for an entity model, not tiles.

**UV `v` grows downward.** The upper half of a tile belongs on the upper half of
a block. A bottom slab shows the *bottom* half of its texture. Getting this
backwards is invisible on stone and obvious on planks.

---

## Not everything is in the block states

A copper golem statue keeps its **pose** in the block entity beside the block,
the way a sign keeps its text. A structure holding four statues in four poses has
one palette entry for all of them, and the pose is in
`structure.palette.default.block_position_data`, keyed by the block's flat index
(x outermost).

`structure_reader.get_block_entity(x, y, z)` reads it and
`structura.core.ENTITY_SHAPES` says which field of which block entity names the
shape. Add to that mapping to support another one — a block entity carries a
great deal that has nothing to do with how a block looks, so only the named
fields are read.

---

## High and low geometry

Every ghost block is geometry the client lights and draws, and Vibrant Visuals
makes that markedly more expensive. A family may declare a simpler form of
itself, named with the `__low` suffix — `bell__low` beside `bell` — and a pack
built with low geometry uses it. A family without one is drawn as it always is,
which is most of them.

`tools/make_low_geometry.py` generates those forms for every family carrying
three or more cubes: the box the detailed shape fits inside, textured with the
window that box covers. **Re-run it after changing a detailed shape**, or the
simple form will still be the old one's outline.

---

## Approximations, and what still wants checking in a world

Geometry numbers and UV values can be checked here. How they look cannot.

- **Copper golem statue poses** are built from the same three pieces moved and
  leaned, not remodelled. They are distinguishable and upright; whether each
  matches the pose the game draws is unverified. `tools/make_statue_poses.py`.
- **Bell and grindstone mountings** move the pieces rather than remodelling
  them. A wall-bracketed grindstone really has no legs; here they are shortened.
- **Hanging signs** do not yet distinguish hanging from a chain, hanging from a
  block, or bracketed to a wall. The states are read (`attached_bit`, `hanging`)
  but there is one shape.
- **Campfires** distinguish lit from extinguished, but the fire itself is not
  modelled — only the four logs.
- **Two block tall flowers** take the block's `down` texture on the lower half
  and `up` on the upper. Bedrock's `side` texture for these is a different
  plant's back and should never be used.

---

## Adding a block

1. Put the id in `block_definition.json` against a shape family.
2. If the family is new, describe it in `block_shapes.json` **and**
   `block_uv.json`.
3. If it turns, give it a `block_rotation.json` entry with both numbers and
   words.
4. If any of its states change how it looks, map them in `nbt_defs.json`.
5. If it is built from more than one cube, give it an `overwrite`.
6. If it now carries three or more cubes, re-run `tools/make_low_geometry.py`.
7. Run `tools/coverage_report.py` and `tools/audit_blocks.py`. Both should
   report nothing.

Keep the tables compact. `json.dumps` explodes short numeric arrays across a
line each, which turns a one-value change into an unreviewable diff;
`tools/lookup_writer.py` edits one family's span and leaves the rest of the file
byte for byte alone.

# Editing blocks

The reference for the five lookup tables a block is described by. For the
knowledge that is not obvious from the formats, such as why a door faced the
wrong way, which textures are lists and where a copper golem keeps its pose, read
[Block Notes](Block%20Notes.md) instead.

Every table is keyed by a **shape family** rather than by a block id, so the
hundred kinds of stair share one description.

| File | Keyed by | Says |
| --- | --- | --- |
| `block_definition.json` | block id | which family draws it |
| `block_rotation.json` | family | how each rotation state turns it |
| `block_shapes.json` | family, then variant | the cubes |
| `block_uv.json` | family, then variant | the texture window per cube per face |
| `nbt_defs.json` | block state name | what that state means |
| `variants.json` | state name | which entry of a texture list a value picks |

`block_shapes.json` and `block_uv.json` **must agree**. A variant in one and not
the other silently falls back to `default`, which is how a half-height cube ends
up wearing a full-height texture.

---

## block_definition.json

`"minecraft:oak_door": "door"`. A block with no entry is skipped and reported,
not drawn. The family name is yours to choose; it only has to match the other
tables.

`"ignore"` draws nothing, for blocks that should not appear at all.

---

## block_rotation.json

A family maps each rotation state to a turn about X, Y and Z in degrees.

```json
"repeater": {"0": [0, 180, 0], "1": [0, -90, 0],
             "2": [0, 0, 0], "3": [0, 90, 0]}
```

Keys are strings. **Give both the numbers and the compass words**, because
Bedrock uses
a numeric `direction` on some blocks and a `minecraft:cardinal_direction` string
on others, and a value the table has no key for is drawn unrotated with no
warning. The numbering differs between blocks; see
[Block Notes](Block%20Notes.md).

---

## block_shapes.json

A family holds one entry per variant, and always a `default`.

```json
"heavy_core": {"default": {"size": [[0.5, 0.5, 0.5]],
                           "offsets": [[0.25, 0, 0.25]],
                           "center": [0.5, 0.25, 0.5]}}
```

| Key | | |
| --- | --- | --- |
| `size` | required | one `[x, y, z]` per cube, as a fraction of a block |
| `offsets` | optional | one `[x, y, z]` per cube; where each starts. Omitted means the origin |
| `rotation` | optional | one `[x, y, z]` per cube, in degrees, turning that cube alone |
| `center` | required | the point the family's own rotation is applied about |

A variant name comes from the block's states, described under `nbt_defs.json`
below. The
names `top`, `open`, `open_hinged` and `side` are used by the code itself for
upper halves, open doors and trapdoors, and side-fed hoppers.

---

## block_uv.json

The same variants, describing where on the texture each cube's faces are cut
from. All six directions must be present, and each must have one entry per cube.

```json
"heavy_core": {"default": {
    "uv_sizes": {"up": [[0.5, 0.5]], "down": [[0.5, 0.5]], "north": [[0.5, 0.5]],
                 "south": [[0.5, 0.5]], "east": [[0.5, 0.5]], "west": [[0.5, 0.5]]},
    "offset":   {"up": [[0.25, 0.25]], "down": [[0.25, 0.25]], "north": [[0.25, 0.5]],
                 "south": [[0.25, 0.5]], "east": [[0.25, 0.5]], "west": [[0.25, 0.5]]}}}
```

- `uv_sizes`: how much of the tile that face takes, as a fraction
- `offset`: where on the tile it starts, from the **upper left**

**V grows downward.** A block sitting on the floor of its cell takes the lower
part of the tile, so its `v` offset is one minus the top of the box.

### overwrite

Optional, and the only way to give the parts of a multi-cube block different
textures. Without it every cube gets the block's same six faces.

```json
"overwrite": {"up": ["@down", "@up", "@north"], "north": ["@down", "@up", "@north"]}
```

One entry per cube, per face:

- a literal path such as `textures/blocks/obsidian` is used as given
- `"default"` leaves that cube's face alone
- `"@up"`, `"@down"`, `"@north"` … mean **whatever this block declares for that
  face**

Prefer the `@` form. It survives a family gaining variants and works for a family
shared by many block ids, so one entry serves every wood a sign comes in.

---

## nbt_defs.json

What a block state means. A state that is not listed is ignored entirely, which
is the usual reason a block looks the same however it is placed.

| Value | Effect |
| --- | --- |
| `rot` | picks a rotation from `block_rotation.json` |
| `variant` | picks an entry from a texture **list**, through `variants.json` |
| `top` | selects the `top` shape variant |
| `data` | the state's **number** names the shape variant |
| `shape` | the state's **value** names the shape variant |
| `open_bit`, `hinge` | door and trapdoor flags |

`data` is for numbers and `shape` for words. Several `shape` states on one block
are joined with `-` in the order the state names sort, so `attached_bit` before
`hanging` gives `"0-1"`.

---

## variants.json

For textures that are declared as a list. Maps a state's value to the index that
picks one.

```json
"rehydration_level": {"0": 0, "1": 1, "2": 2, "3": 3}
```

Keys are strings even when the state is a number.

---

## Working on the tables

- Keep them compact. `json.dumps` explodes short numeric arrays across a line
  each, which turns a one-value change into an unreviewable diff.
  `tools/lookup_writer.py` replaces one family's span and leaves the rest of the
  file byte for byte alone.
- Be sparing with cubes. Since Vibrant Visuals arrived, the cost of drawing a
  bone rose sharply, and every ghost block is one. A family carrying three or
  more cubes should have a simplified form; `tools/make_low_geometry.py`
  generates them, and wants re-running after a detailed shape changes.
- Check your work:

```bash
python tools/coverage_report.py     what the bundled structures drop
python tools/audit_blocks.py        every declared block resolved to a texture
```

Both should report nothing.

# Working on Structura

Standing rules and the project information worth having before touching
anything.

---

## The project

**Structura** — inspired by Litematica. A Python desktop program that turns a
`.mcstructure` file into a Bedrock resource pack (`.mcpack`). The pack replaces
the vanilla armor stand client entity with one that renders when off screen and
carries every block of your structure as a bone in its model, drawn as
semi-transparent "ghost blocks" so you can see where the real blocks go.

There is no behaviour pack and no script API anywhere in this project. Whatever
the generated pack does, it does with geometry, render controllers, animations
and textures.

## This is a private fork

Releases are built locally with `python build.py`, not by CI. The in-app update
button is hidden behind `SHOW_UPDATE_BUTTON` in `structura.py`; the updater and
the `--update` flag still work and are kept for when the fork gets an update
source of its own. Do not add build or release workflows.

---

## Layout

```
structura.py             entry point: the CLI, and the handoff to the window
structura_gui.py         the window, on CustomTkinter
app_settings.py          settings and translated strings, shared by both
paths.py                 where data lives, in a checkout and inside the bundle
lang_icons.py            the language picker's code badges
lang_fun.py              the constructed languages, generated from English
structura_core.py        the pipeline: structure in, pack folder out
structure_reader.py      .mcstructure NBT parsing
armor_stand_geo_class.py block -> geometry and UV; the biggest and trickiest file
armor_stand_class.py     the armor_stand client entity
animation_class.py       layer pose animations
render_controller_class.py / big_render_controller.py
manifest.py              the generated pack's manifest
tech_pack.py             folds the TechPack submodule into a generated pack
jsonc.py                 reads Bedrock's permissive JSON; shipped, not a tool
version.py               reads the VERSION file
lang_parse.py            reads lookups/langs.csv
updater.py               lookup-table updater (disabled in this fork)
build.py                 local release build

lookups/                 the lookup tables this project owns
Vanilla_Resource_Pack/   trimmed vanilla pack the generator reads textures from
tools/                   one-off and maintenance scripts, not shipped
                         (make_icon.py, make_screenshots.py, audit_blocks.py,
                          coverage_report.py, sync_vanilla_pack.py)
tests/                   unittest suite
test_structures/         .mcstructure files to generate against
docs/                    user-facing documentation
```

`CommunityVanillaResourcePack/` is a git submodule and is reference material
only; nothing in the program reads it at runtime. `be_tech_pack/` is also a
submodule, but it is **not** only reference material any more — `tech_pack.py`
reads it when the TechPack toggle is on, and `build.py` ships the parts a
generated pack needs beside the executable.

---

## The window

`structura_gui.py` is the whole interface; `structura.py` is the command line
and one call into it. They share `app_settings.py` so neither has to import the
other.

It is built on **CustomTkinter**, which is tkinter underneath -- so the frozen
build stays roughly the size it was -- but draws modern widgets and can follow
the desktop's light or dark setting. `darkdetect` is what answers that question;
where it cannot (Linux), the theme falls back to dark rather than guessing.

There is **no basic and advanced split any more**. One screen: structures on the
left, everything describing the pack on the right, status along the bottom. A
single structure needs no name tag; the second one added makes tags required,
and the window says so as it is typed.

Things worth knowing before changing it:

- **`Field` is the composite entry.** CustomTkinter cannot inset an entry's
  text, and a picture placed over one covers the characters rather than moving
  them. So `Field` owns the border and holds a borderless entry beside a mark --
  the name tag's item texture, an axis letter. Anything that needs something
  *inside* a field goes through it.
- **The name tag fields are a fixed width**, not a weighted column. Rows have
  different file names, and a proportional field made every row a different
  length.
- **The window opens with no structures.** An empty row is something the user
  has to notice and delete.
- **A CustomTkinter entry bound to a `textvariable` never shows its
  placeholder.** The variable is what makes validation live, so every hint that
  used to be placeholder text -- optional/required on a name tag, the pack name
  label -- is a real label instead. Do not reintroduce `placeholder_text` on a
  field that has a variable; it will silently never appear.
- **A `CTkToplevel` gets Tk's default icon** unless told otherwise, and it has to
  be told after the window exists. `apply_icon()` does it on a delay, and the
  main window repeats it because CustomTkinter resets the icon while it finishes
  setting up.
- **The build runs on a worker thread** and talks back through a queue that the
  main thread drains in `after()`. Tk is not thread safe; nothing off the main
  thread may touch a widget.
- **The status line is always saying something.** A finished build's message is
  `sticky` so re-validating does not wipe the one line that says it worked.
- **Big build mode borrows the offset fields and the name tags.** Their values
  are stashed and handed back when it is switched off, so flipping it twice
  leaves the window exactly as it was. Anything else that mode takes over has to
  do the same.
- Screenshots in the README are generated by `tools/make_screenshots.py` from the
  running window. Change the interface, re-run it.
- **Settings live in `.structura`** -- next to the executable if one is there,
  which makes the program portable, and otherwise in the home directory, not
  beside the program, so they survive
  replacing the executable and work when it is run from a folder the user cannot
  write to. An older `settings.json` is read once to carry a choice over.

### The generated pack's name and description

`manifest.py` owns both. The name shown in game is prefixed -- `Structura: <what
the user typed>` -- but **the UUID is still derived from the bare name**, because
folding the prefix in would have made every pack built by an older Structura look
like a different pack to the game and left players holding two copies.

The description is one field with newlines between its parts: the user's own note
first, then the name tags, then the TechPack version if bundled, then the credits
line. The credits colours are Minecraft formatting codes and each author keeps
the colour they have always had.

---

## Where the data lives

The release is a **single self-contained executable**. `lookups/`,
`Vanilla_Resource_Pack/`, the shipped part of `be_tech_pack/`, `VERSION` and
`images/` are packed inside it and unpacked at run time into the folder
PyInstaller points `sys._MEIPASS` at.

**Every data read goes through `paths.py`.** A hardcoded `open("lookups/...")`
works in a checkout and fails in a release, which is the worst way for a bug to
behave. `paths.data()` searches, in order: beside the executable, inside the
bundle, the source tree, the working directory.

Beside the executable wins on purpose, and two things depend on it:

- the updater writes lookup drops there, and a bundle is read only
- anyone hand-editing a lookup table can drop the folder next to the exe

`tests/test_paths.py` builds a pack with the working directory set to an empty
temporary folder. That is the cheap way to catch a module that still assumes the
checkout is the working directory -- a missing `import paths` shows up there as
the NameError it is, rather than only in a release nobody has run yet.

## Languages

`lookups/langs.csv` holds the real ones, one column per language. The
constructed ones -- Enchanting, Pirate Speak, LOLCAT, Shakespearean and
upside-down English -- are **not** in the CSV: `lang_fun.py` generates them from
the English column when the table is loaded. Sixty-odd strings times five joke
languages is three hundred cells nobody would keep in step; generated, they cover
whatever label is added next for free.

Two things to keep in mind when touching `lang_fun.py`:

- **Format placeholders are protected.** The transforms run only over the text
  between `{}` markers. Reversing "Built {}" without that protection produces
  "}{ ..." and the next finished build raises on `.format()`.
- **Enchanting is an evocation, not the real alphabet.** Minecraft's enchanting
  table script is a *font* -- the glyphs are in the resource pack as
  `font/ascii_sga.png` and there is no Unicode block for them -- so no string of
  characters can be the genuine article. Making it real would mean building a
  font from that sheet and loading it privately at run time.

Badges are drawn by `lang_icons.py`: two or three letters, amber for real
languages and a distinct hue per constructed one, so the picker shows at a glance
which entries are a joke.

---

## Finish every round with a version bump

**Every time a set of tasks is completed, bump the version.** This is not
something to ask about or offer; it is part of finishing the work. If a round of
changes is done and the version has not moved, the round is not done.

- **Major** (`1.2.0` → `2.0.0`) — a change that breaks packs already in use, or
  a change so large it is not worth enumerating the minor and fix changes that
  went into it.
- **Minor** (`1.2.0` → `1.3.0`) — new behaviour a user can notice: a new
  setting, a new control, a change to what an existing feature does, newly
  supported blocks.
- **Fix** (`1.2.0` → `1.2.1`) — refinements to what is already there: bug fixes,
  texture and lookup-table iterations, wording, layout, internal restructuring
  with no visible change in behaviour.

When a round contains both a minor and a fix, the minor bump wins and the fix
digit resets to zero. When the major digit is incremented, the minor and fix
digits reset to zero.

The user will sometimes say a change "rolls into" the previous one and does not
increment the counter, or will name the digit to move to. That overrides the
rule for that round.

### Where the version lives

`VERSION` at the repository root is the source of truth. `version.py` reads it —
looking beside the executable first, so a frozen build finds the copy `build.py`
puts in the release zip. It reaches the window title, the release zip's name and
the generated pack's manifest version. Nothing else should hardcode a version.

---

## Every bump ships with a summary and a commit message

Hand over both in the same reply as the bump, without being asked, at the end
after describing the work. They are written for different readers and should not
be the same sentence.

**Release summary** — one or two sentences on what is new and what changed, in
prose. Add a short clause only if something breaks for existing users and they
have to act on it. Not a formatted document, not a section per subsystem, not an
artifact. Write it directly in the reply.

**Commit message** — one line, a few words, in the user's own log style. No
body, no bullets, no test counts. Real examples from the log:

```
First release
Bugfixes
Fixed and updated items
Revamped the compass to the ledger. More item fixes. Bracket customization.
Changed Sigil watermark in the menu
```

Brevity here is about summaries and commit messages only. Detailed technical
explanation while working through a problem is welcome.

---

## How a pack gets built

`structura.structura(pack_name)` makes a folder, then:

1. `add_model(name_tag, file)` and `set_model_offset(name_tag, offset)` register
   each structure. **`set_model_offset` is not optional** — the offset defaults
   to `None` and the geometry builder subscripts it.
2. `generate_with_nametags()` reads each structure, and for every non-air block
   calls `armorstandgeo.make_block`, which resolves the block through the lookup
   tables into cubes with UVs and appends them to a per-layer bone.
3. `compile_pack()` writes the manifest, copies the icon, zips the folder and
   renames it to `.mcpack`.

Blocks are batched into bones named `slice_<y>`, parented to `layer_<y % 12>`.
The layer bones are what the pose animations scale up and down, which is how
shift-right-clicking an armor stand steps through the build.

### Driving it from something other than the GUI

`structura_core` is the API any front end uses, and it is deliberately the only
thing a future service would need. Everything it produces is available as data
as well as as a file, because a service wants the former:

| Call | Gives you |
| --- | --- |
| `compile_pack()` | the path to the finished `.mcpack` |
| `get_nametags()` | the name tags in the pack |
| `get_block_lists()` | `{name tag: {block: count}}` |
| `get_material_list()` | every block the pack needs, summed across models |
| `get_skipped(write_file=False)` | `{block: {variant: count}}` that could not be built |
| `get_unique_blocks_count()` | how many distinct blocks the pack covers |
| `get_lookup_version()` | which lookup drop built it |

Keep it that way. A hosted version of Structura belongs in its own project that
imports this one; anything that knows about a queue, a bucket, a bot or a user
account does not belong in this repository. The previous attempt lived here as
`lambda_function.py` and had to reach into `structure_files[...]["block_list"]`
because the accessors above did not exist.

**A block that fails to resolve is not an error.** `make_block` raises,
`_add_blocks_to_geo` catches it, and the block is recorded in
`unsupported_blocks` and reported in the skipped list. That is why a missing
`block_definition.json` entry produces a silently incomplete model rather than a
crash — and why the audit in `tools/` matters.

### The pack icon

`pack_icon.png` must be a valid PNG, square, and **256×256** — the size
Microsoft documents for the pack selection screens (`CPACKICON101`–`104` in the
Creator Tools validation reference). There is one per pack root; a subpack
carries its own, nothing else should.

`tools/make_icon.py` regenerates both icons the project ships —
`lookups/pack_icon.png` at 256×256 and `pack_icon.ico` from 16 px to 256 px —
by rendering the isometric S cube over `background_slimelab.png`. The grid
colour, its alpha and the S material are the constants at the top of that file.
Nothing is stored that the script cannot rebuild.

**No tool checks the icon rules.** This section used to claim the audit did;
it never has. If it matters, the check belongs in `tools/audit_blocks.py`.

### The lookup tables

| File | What it holds |
| --- | --- |
| `lookups/block_definition.json` | block id → shape family. Missing entry means the block is skipped |
| `lookups/block_shapes.json` | shape family → cube sizes, offsets and the group pivot, per variant |
| `lookups/block_uv.json` | shape family → per-face UV sizes and offsets, per variant, plus texture overrides |
| `lookups/block_rotation.json` | shape family → rotation for each rotation state |
| `lookups/nbt_defs.json` | block state name → what it means (`rot`, `top`, `variant`, `data`, `open_bit`) |
| `lookups/variants.json` | variant state value → index into a terrain_texture list |
| `lookups/material_list_names.json` | block id → the name shown in the block list |
| `lookups/langs.csv` | UI strings, one column per language |

`block_shapes.json` and `block_uv.json` must agree. A variant that exists in one
and not the other silently falls back to `default`, which is how a snow layer
ends up wearing a full-height texture. Add variants to both.

**UV V grows downward.** The upper half of a texture tile belongs on the upper
half of a block. A bottom slab shows the *bottom* half of its texture; a top
slab shows the top half. Getting this backwards is invisible on stone and
obvious on planks.

---

## What an `.mcpack` actually is

A ZIP archive with the extension changed. Everything that makes one work or not
work is about the archive's shape:

- **The pack root is the archive root.** `manifest.json` must be a top-level
  entry. If the archive contains a wrapper folder, Minecraft imports it without
  an error and the pack never appears in the list.
- **Entry paths use forward slashes**, always, whatever the host OS.
- No `__MACOSX`, no `.DS_Store`, no `Thumbs.db`.
- Classic 32-bit ZIP only. No ZIP64, no encryption.

### Manifest rules

`manifest.py` is the only thing that writes a generated pack's manifest.

- `format_version` is `2`, exactly one `resources` module, no scripts.
- **UUIDs are derived, not random.** `uuid5` over a fixed Structura namespace
  plus the pack name, so regenerating a pack replaces the one already in the
  player's list instead of appearing as an unrelated pack. Never go back to
  `uuid4` here; the accepted cost is that two people who pick the same pack name
  get the same UUID.
- The pack version is the Structura version, from `VERSION`.

### Bundling TechPack

`tech_pack.py` folds the `be_tech_pack` submodule into a generated pack when the
toggle is on — `set_tech_pack(True)`, the **Bundle TechPack** checkbox, or
`--tech_pack`.

This exists because the two projects collide head on. Both replace
`entity/armor_stand.entity.json`, a client entity file replaces the vanilla one
rather than merging with it, and **between two packs only the higher in the
player's list is read at all**. Applying Structura and TechPack side by side
does not half-work: whichever sits lower is ignored completely. There is no
ordering that runs both, which is why bundling is the only answer and why the
README says to disable the standalone TechPack while a bundled pack is active.

The merge lives on `armorstand.merge_description`, not in `tech_pack.py`, because
it is about the shape of a client entity file rather than about TechPack.
Structura wins every conflict, and one of them matters: `geometry.default` has to
stay on `geometry.armor_stand.larger_render`, or the model stops drawing the
moment the stand leaves the screen. Script order matters too — the pose
controllers have to run before anything that reads the pose index, and TechPack's
`spawner_radius` entry does exactly that.

Two things worth knowing:

- TechPack's own `scripts.animate` asks for `controller.pose` and
  `controller.wiggling` without declaring them in its `animations` map — the
  drift this file warns about, in somebody else's copy. Bundled with Structura,
  which does declare both, nothing is left dangling.
- Both projects ship `models/entity/armor_stand.larger_render.geo.json` and both
  declare the same geometry id. The files are currently byte-identical, which is
  the only reason `copy_assets` can skip the collision instead of resolving it.
  A test asserts they stay identical.

### Bedrock is case-sensitive; Windows is not

`textures/Density` resolves to `textures/density.png` on a Windows dev machine
and resolves to nothing on Android, iOS and consoles, where it draws an
untextured surface with no error anywhere. Match the case the files actually
have on disk.

### Pack JSON is not JSON

Bedrock's parser is more permissive than `json.loads`, and the vanilla packs use
it: `//` comments, trailing commas, and a UTF-8 BOM. The community submodule's
`blocks.json` and `terrain_texture.json` both carry comments. Read them through
`tools/jsonc.py`, never `json.load`, or valid content will be reported as
broken. The trimmed `Vanilla_Resource_Pack/` in this repository is plain JSON
and is safe either way.

### Replacing the vanilla armor stand

`armor_stand_class.py` carries a hardcoded copy of vanilla's
`armor_stand.entity.json` description with this project's geometry and textures
added. A client entity file in a resource pack **replaces** the vanilla one;
they do not merge. Vanilla's own animation and render controllers keep asking
for the short names vanilla's copy declared, so every name the copy fails to
carry over is a `can't find animation <name>` in the content log and a vanilla
animation that stops playing.

This drifts on its own: Mojang adds a short name in an update and the hardcoded
copy, which never changed, is suddenly missing it. When a Minecraft update
lands, diff the `animations`, `scripts.animate` and `render_controllers` lists in
`armor_stand_class.py` against
`CommunityVanillaResourcePack/entity/armor_stand.entity.json`.

---

## Keeping the vanilla pack current

`Vanilla_Resource_Pack/` is a trimmed vanilla pack, hand-merged over years. Some
of its textures are **deliberately** not vanilla:

- biome-tinted textures are pre-tinted, because ghost blocks cannot run the
  colormap (`grass_top`, `tallgrass`, `vine`, the stems, `water_*_grey`,
  `redstone_dust_cross`)
- some are made more opaque so the ghost stays visible after the alpha pass
  (`glass_*`, `slime`, `hopper_top`)

`tools/sync_vanilla_pack.py` encodes those rules. Run it against the community
submodule rather than copying files by hand, and read what it reports before
applying anything. `tools/audit_blocks.py` resolves every declared block down to
a texture file and reports what does not.

---

## Comments describe how things work, not how they were decided

Write comments that explain mechanism, logic flow, and anything a reader needs
in order to change the code safely. **Do not** record decision history: what was
tried and rejected, what a previous version did, which bug prompted a change,
what was weighed against what. That belongs in the commit log and
`PROJECT_REVIEW.md`.

Empirical facts about engine behaviour are worth keeping, stated as facts — "the
X axis runs opposite to the Z axis here" rather than "this took three builds to
work out".

Match the surrounding density: module headers carry a short orientation,
non-obvious logic carries an inline comment. This codebase is lightly commented
and inconsistently formatted; match the file you are in rather than reformatting
around your change.

---

## Working habits

- **Isolate one variable at a time.** Changing two things and then attributing
  the result to one of them has produced wrong diagnoses here more than once.
- **Do not claim a causal link that has not been tested.** A hypothesis stated
  once becomes a fact if it is repeated; say "untested" and name the check that
  would settle it. The user tests in-game and reports back — give them the
  specific thing to look at, and say which observations would *not* prove it.
- **In-game behaviour is not knowable from here.** Rendering, placement, z-fighting
  and transparency need a live world. Geometry numbers and UV values can be
  checked here; how they look cannot.
- **Prefer Python patch scripts over shell heredocs** for multi-line source
  edits. `\n` inside a heredoc has repeatedly become a literal newline and
  corrupted string literals. Write the script with the Write tool, or anchor on
  text containing neither.
- **Re-compact JSON after writing it with `json.dumps`**, which explodes short
  numeric arrays across lines. The lookup tables are kept compact, and a
  reformatted table makes a one-value change unreviewable.
- **The test structures are the regression suite.** `tools/coverage_report.py`
  builds against all 108 of them and prints what `get_skipped()` reports, which
  is the fastest way to see whether a lookup change broke something. It drives
  the real pipeline rather than reimplementing the state translation, so the
  answer is what a user's build would actually produce. It should print zero.

---

## Running, testing and building

```bash
python structura.py                                    the window
python structura.py --structure in.mcstructure --pack_name Name    CLI
python -m unittest discover -s tests -t .              tests
python build.py                                        release zip in dist/
python tools/make_screenshots.py                       refresh the README's shots
python tools/coverage_report.py                        what the test structures drop
python tools/audit_blocks.py                           what does not resolve
python tools/make_icon.py                              regenerate both icons
```

`lookups/` and `Vanilla_Resource_Pack/` are opened by relative path, so all of
these must run from the repository root.

---

## Reference

- Bedrock samples: https://github.com/Mojang/bedrock-samples
- Community documentation: https://wiki.bedrock.dev/
- Vanilla listings:
  https://learn.microsoft.com/en-us/minecraft/creator/reference/content/vanillalistingsreference/?view=minecraft-bedrock-stable

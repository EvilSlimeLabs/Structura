# Project review

A pass over the desktop program, the lookup tables and the build. Everything
here was reproduced against the working tree unless it says otherwise; the few
items that need a live Minecraft client to settle say so.

Items already fixed while writing this are not listed. Block coverage is a
separate list — see `BLOCK_COVERAGE_GAPS.md`.

---

## Crashes

**`lang["Error"]` raises `KeyError` on every validation path.**
`lookups/langs.csv` calls the string `error`, lower case. `structura.py` asks
for `"Error"` at lines 187, 189, 228, 233, 236 and 240 — which is every message
box the GUI shows when the user gets something wrong. Browsing without picking a
structure, reusing a name tag, an empty pack name, a pack that already exists:
all of them raise instead of explaining. Either rename the CSV key or fix the
six lookups; fixing the lookups is smaller and keeps the other translations
valid.

**A model added without an offset crashes the generator.**
`structura.generate_with_nametags` computes a default offset when
`structure_files[name]["offsets"]` is `None`, assigns it to a local named
`offset`, and never writes it back. `_add_blocks_to_geo` then passes the `None`
straight to `armorstandgeo`, which does `self.offsets[0] += 0.5` and raises
`TypeError: 'NoneType' object is not subscriptable`. Reproduced with
`add_model()` followed by `generate_with_nametags()`. The GUI and CLI both
happen to call `set_model_offset` first, so this only bites callers using
`structura_core` as a library — `APItest.py` among them.

**`compile_pack(overwrite=True)` deletes a file that may not exist.**
The `os.remove` of the old `.mcpack` runs unconditionally when `overwrite` is
set, before the rename, so overwriting a pack that is not actually there raises
`FileNotFoundError`. The CLI sidesteps it by removing the file itself and then
calling `compile_pack()` with no argument, which means the parameter is dead in
both shipped entry points and broken for anyone else.

---

## Wrong output

**Partial-height blocks get a full-tile texture stretched over them.**
`make_block` picks `block_uv` before it applies the `data` variant:

```python
block_uv = self.block_uv[block_type]["default"]
if shape_variant in self.block_uv[block_type].keys():
    block_uv = self.block_uv[block_type][shape_variant]
if str(data) in self.block_uv[block_type].keys():
    shape_variant = str(data)          # block_uv is not re-read
```

So when `data` selects a variant, `shape_variant` changes but `block_uv` keeps
pointing at `default`. Nine shape families have variants in
`block_shapes.json` with no counterpart in `block_uv.json` and fall through the
same way: `door` top, `stairs` top, `hopper` side, `lever` on, `double_plant`
top, `repeater` and `unpowered_repeater` 0, `sea_pickle` 0–3, `top_snow` 0–6,
and all 63 `vine-multi` entries.

The visible result: a one-layer snow block is 2 pixels tall and wears the whole
16-pixel snow texture squeezed into those 2 pixels. Confirmed by generating
`snow_layer` at data 0, 3 and 6 — all three come out with
`uv_size [1, 1]` regardless of height. This is the same defect class as the slab
side-face misalignment, and fixing it means adding the missing `block_uv`
variants and re-reading `block_uv` after `shape_variant` is finalised.

**Trapdoor bottom halves probably have the same half-texture swap as slabs
did.** `block_uv["trapdoor"]["default"]` uses a V offset of 0 for a block that
sits in the bottom 3 pixels of its cell, so it shows the top of the texture
where the game shows the bottom. The `top` variant, which does sit at the top,
also uses 0 and is correct. Untested — trapdoor textures are close to
vertically symmetric, so this needs a side-by-side look in a live world against
a wood trapdoor before anyone changes it.

**`self.longestY` is never assigned.** `_add_blocks_to_geo` writes a local
`longestY` inside the `if`, so `self.longestY` stays 0 and the comparison is
always true. `update_animation` is therefore always true and the `else` branch
is unreachable. No visible effect today, because `animations.insert_layer` just
reassigns dictionary keys and is idempotent — but the code reads as if it
guards against something, and it does not.

---

## Robustness

**Windows-only path separators.** `structura_core.get_lookup_version` and
`structura.update` both open `r"lookups\lookup_version.json"`. On Linux and
macOS that is a single filename containing a backslash, so the version reads as
"No version found" and the updater raises. The repository ships a `start.sh`, so
those platforms are meant to work. Every other path in the project already uses
forward slashes.

**`updater.update` extracts a downloaded archive over the working directory**
with `extractall(path="")` and no checksum, signature or manifest of what it is
allowed to replace. CPython sanitises member paths so this is not a directory
escape, but a wrong or hostile response still overwrites arbitrary files under
the program directory. At minimum the extraction should be restricted to
`lookups/`.

**`--overwrite` is `type=bool`.** argparse applies `bool()` to the string, so
`--overwrite false` and `--overwrite 0` both come out true. It wants
`action="store_true"`.

**A partial CLI invocation silently opens the GUI.** The CLI branch is
`if args.structure and args.pack_name`. Passing only one of the two falls
through to `Tk()` with no message, which on a headless machine fails somewhere
much less obvious.

**`--debug` is parsed and never read.** The module-level `debug` flags in
`structura_core.py` and `armor_stand_geo_class.py` are what actually control
debug behaviour, and they are edited by hand. Wiring the flag to both would make
the option real.

**Eighteen bare `except:` clauses**, including three in the block pipeline
(`structura_core.py:235`, `structure_reader.py:78` and `:152`). The one in
`_process_block` swallows anything raised while coercing a rotation state to
`int`, which is how a malformed state quietly becomes a string rotation instead
of an error.

**`armorstandgeo.__init__` takes `offsets=[0,0,0]` as a default and then mutates
it** (`self.offsets[0] += 0.5`). Two constructions that both rely on the default
would see the offset accumulate. Nothing does that today; it is a trap for the
next caller.

---

## Build and release

**The build workflow never fires on this branch.** `.github/workflows/build.yml`
triggers on pushes to `main`; this repository's default branch is `master`.
Every build so far has come from `workflow_dispatch`.

**Nothing runs the tests.** The workflow bundles and uploads; it does not
install and run `tests/`. And `tests/` has no `__init__.py`, so
`python -m unittest discover -s tests -t .` fails with "Start directory is not
importable" — the tests only run when named explicitly
(`python -m unittest tests.test_slab_states`). Adding the package marker and a
test step is a small change that would have caught the slab regression.

**`structura.spec` is not used.** The workflow calls
`pyinstaller --clean --onefile structura.py`, which regenerates a spec from
scratch and ignores the checked-in one. The two will drift.

**`VERSION` is not read by anything.** `CLAUDE.md` says the VERSION file is the
source of truth and that the build copies it where it is needed, but no code,
workflow or spec references it. `structura.py` hardcodes
`structura_update_version = "Structura1-7"`, and `manifest.py` hardcodes the
generated pack's version at `[0, 0, 1]`. Pick one source and have the others
read it.

**`requirements.txt` mixes two applications and pins stale versions.**
`PyNaCl`, `cffi` and `pycparser` are only needed by `lambda_function.py`;
`boto3`, `botocore` and `PyJWT`, which that file also imports, are absent, so
the list does not actually install the Lambda either. `pooch`, `platformdirs`
and `packaging` are imported by nothing in the repository. `certifi==2022.12.7`,
`urllib3==1.26.14` and `requests==2.28.2` are exact pins three years old with
published advisories. Splitting desktop and Lambda requirements and loosening
the pins on the transitive ones would fix both problems.

**Generated packs get fresh UUIDs on every build.** `manifest.py` calls
`uuid.uuid4()` for the header and module every time. Regenerating a pack after
tweaking a structure therefore produces a pack Minecraft treats as unrelated to
the one already applied to the world, rather than an update of it. Deriving the
UUIDs deterministically from the pack name would let a rebuild replace the old
pack in place. Worth confirming in game before changing — it is a behaviour
users may have built habits around.

---

## Structure and maintenance

**`CLAUDE.md` describes a different project.** It says the source lives in
`src/` (it is at the repository root), and it documents an `.mcpack` build with
`tools/lib/zip.js`, `tools/lib/jsonc.js`, `npm run audit`,
`tools/external-refs.json`, `tools/vanilla-baseline.json`, a `package.json` the
manifest must agree with, and a rule about stable versus beta
`@minecraft/server` script APIs. None of that exists here, and this project
ships no behaviour packs or scripts at all. The genuinely applicable parts — the
version bump ritual, the comment policy, the working habits, the note that
Bedrock is case-sensitive and that pack JSON is not JSON — are worth keeping;
the rest is misleading.

**`lambda_function.py` is a 26 KB fork of the desktop pipeline.** It carries its
own copies of the block processing and pack assembly logic. The slab fix in this
round had to be reasoned about separately for it. Either it imports
`structura_core` or the shared parts move into a module both can use.

**Repository root is doing too much.** `APItest.py`, `speed_test.py`,
`build all .py` (a filename with spaces), `creating AWS layers.txt`,
`merge_terrain_texture.py` and `Vanilla_Resource_Pack/merge_blocks.py` are all
loose at the top level alongside the program. Moving the program into a package
and the one-off scripts into `tools/` would make the PyInstaller entry point
obvious and stop `structura.py` from being a module that opens a window as a
side effect of import.

**`structura.py` builds the GUI at import time.** Everything from `root = Tk()`
down runs on import, which is why the CLI branch has to `sys.exit(0)` before
reaching it and why the module cannot be imported by a test. A `main()` behind
`if __name__ == "__main__":` would fix both.

**No merge script for the vanilla pack.** Bringing `Vanilla_Resource_Pack` up to
date this round meant classifying 133 differing textures by hand to separate the
ones Structura deliberately recoloured or made more opaque from the ones that
were simply stale. That knowledge is now only in the git history. A script that
holds the keep-list explicitly, syncs the rest from the submodule, and pulls the
`blocks.json` and `terrain_texture.json` entries for a named set of blocks would
make the next Minecraft update a command instead of an investigation. This is
the single highest-leverage item in this file, because
`BLOCK_COVERAGE_GAPS.md` is 158 entries long and most of them are that same
merge.

**The language selector is not built.** `langs.csv` carries English, Ukrainian,
Spanish and Simplified Chinese, `settings.json` stores a `lang` key, and
`langs.csv` even has a `language` label — but nothing in the GUI sets it, so
changing language means editing `settings.json` by hand. `OptionMenu` is
imported for a menu that was never added. Also `lang = langs[settings["lang"]]`
raises `KeyError` on an unrecognised value rather than falling back to English.

**Dead code worth deleting.** `models[name_tag]["opacity"]` is stored per model
and never read (transparency is one global control). `offsetLbLoc` is assigned
at module level and again inside `box_checked`, and read nowhere.
`armorstandgeo.excluded` duplicates `structura.exclude_list`.
`export_big` writes the identical texture file once per layer.
`get_skipped` only writes its report when more than one block was skipped, so a
single unsupported block produces no file.

**Generated packs contain the source structure.** `generate_with_nametags`
copies the `.mcstructure` into the pack root. For the single-model case the
name tag is the empty string, so the pack ships a file literally called
`.mcstructure`. If this is deliberate — so a pack can be regenerated from
itself — it deserves a comment; if not, it is dead weight in every download.

---

## Suggested order

1. The three crashes. They are small and two of them are one-liners.
2. `tests/__init__.py`, a test step in CI, and the workflow branch. Everything
   after this is safer with those in place.
3. The `block_uv` variant lookup and the missing variants. This is the largest
   visible-quality win and it is confined to two lookup tables and one function.
4. The vanilla-pack merge script.
5. `BLOCK_COVERAGE_GAPS.md` priority 1, then 2, using that script.
6. `CLAUDE.md`, `requirements.txt` and the repository layout.

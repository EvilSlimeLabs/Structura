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

Releases are built locally with `python build.py`, not by CI, and uploaded to
the project's own GitHub releases by hand. **Do not add build or release
workflows.**

**The window is Windows only.** The release is built on a Windows machine, so
`Structura.exe` and `Structura-cli.exe` are the only executables that exist.
macOS and Linux get the command line through `pip install structura`. Do not
write documentation promising a Linux or macOS build; the README claimed one for
a long time and it has never been produced.

**Upload `dist/SHA256SUMS.txt` with the binaries.** `build.py` writes it over
everything the release carries, and the updater refuses to install a build whose
fingerprint the release does not publish. A release missing that one file is a
release nobody can update to.

**The program updates itself from those releases.** `structura/updates.py` asks
the GitHub API for the latest release, and if its tag is a later version than
the running one and it carries an asset named the way the running executable is,
it offers to replace it. Nothing about the upstream update server survives; this
points at this repository and nowhere else.

That whole feature rests on the repository being **public**, because the release
API and the download are unauthenticated. While it is private every check comes
back as "up to date", quietly, which is the same answer as no network.

---

## Layout

Everything importable is one package. `from structura import Structura` is the
whole API, and a service that wants to run Structura vendors one directory rather
than fourteen paths.

Inside it, the pieces are grouped by what they are for: `pack/` turns a structure
into a pack, `cli/` is the command line, `ui/` draws the window. **None of them
import each other.** What more than one of them needs — the settings, the paths,
the language tables — sits beside them at the top of the package, and so does
`core.py`, which is what drives all three.

**`cli/` must not reach into `ui/`.** That is what lets the command line build
leave the interface out, and `structura_cli.spec` excludes `structura.ui`
outright so a build fails rather than quietly growing by six megabytes if it ever
does. The language tables sit outside `ui/` for the same reason: `settings` needs
them, and both sides need `settings`.

```
build.py                 local release build
structura.spec           freezes structura/__main__.py -> Structura.exe
structura_cli.spec       freezes structura/cli/__main__.py -> Structura-cli.exe

structura/               everything importable, and everything it reads
  __init__.py              exports Structura; never mentions the window
  __main__.py              entry point: dual use -- arguments build, none opens
  app.py                   the dual use decision, so __init__ stays clean
  core.py                  the pipeline: structure in, pack folder out
  settings.py              settings, and the strings both sides label things with
  lang_parse.py            reads lookups/lang/, one file per language
  system_locale.py         what language the desktop is set to, for a first launch
  updates.py               whether a newer release is out, and swapping it in
  paths.py                 where data lives, in a checkout and inside the bundle
  version.py               reads the version out of pyproject.toml
  jsonc.py                 reads Bedrock's permissive JSON; shipped, not a tool

  cli/                     the command line
    __main__.py              entry point: the command line alone, no window
    arguments.py             what the program accepts, for both entry points
    commands.py              building a pack
    console.py               output from a build frozen without a console

  pack/                    building a pack
    structure_reader.py      .mcstructure NBT parsing, and block entity data
    armor_stand_geo_class.py block -> geometry and UV; the biggest and trickiest
    armor_stand_class.py     the armor_stand client entity
    animation_class.py       layer pose animations
    render_controller_class.py / big_render_controller.py
    manifest.py              the generated pack's manifest
    tech_pack.py             folds the TechPack submodule into a generated pack

  ui/                      the window
    structura_gui.py         the window, on CustomTkinter
    ui_icons.py              the drawn interface glyphs and the pack icon control
    ui_fonts.py              registers the bundled faces, one per language
    lang_icons.py            the language picker's code badges

  lookups/                 the lookup tables this project owns
    lang/                    one .lang file per language, named for its locale
  Vanilla_Resource_Pack/   trimmed vanilla pack textures are read from
  fonts/                   the three bundled faces, with their licences
  images/                  the two pictures the running program opens
  techpack/                TechPack's assets, staged from the submodule

art/                     source art the icons are generated from, and
                         readme_header.png, which the README opens with;
                         nothing here goes into a build
tools/                   one-off and maintenance scripts, not shipped
                         (make_icon.py, make_screenshots.py, make_fonts.py,
                          audit_blocks.py, coverage_report.py,
                          sync_vanilla_pack.py, lookup_writer.py,
                          make_low_geometry.py, make_bookshelf.py,
                          make_statue_poses.py, fix_problem_blocks.py,
                          make_block_forms.py, make_growth_forms.py,
                          make_furniture_forms.py, make_head_forms.py,
                          make_container_forms.py, make_banner_textures.py,
                          make_string_texture.py, stage_tech_pack.py,
                          lang_fun.py, make_special_languages.py)
tests/                   unittest suite
test_structures/         .mcstructure files to generate against
docs/                    user-facing documentation, including Block Notes.md,
                         which is what to read before touching a block
```

`CommunityVanillaResourcePack/` and `be_tech_pack/` are git submodules and
neither is read at run time. The community pack is reference material for
`tools/sync_vanilla_pack.py` and `tools/audit_blocks.py`. TechPack is the source
`tools/stage_tech_pack.py` copies from — `structura/techpack/` is what the
program actually reads.

---

## Two builds, one command line

`structura/__main__.py` is dual use: give it a structure and a pack name and it
builds one in the terminal, give it nothing and the window opens.
`cli/__main__.py` is the same command line with the window left out of
the bundle. Neither holds any argument parsing of its own -- both call
`cli.main`, which returns `cli.NOTHING_ASKED` when there was nothing to act on
and lets the entry point decide what that means.

A build frozen without a console has nowhere to print on Windows, which would
make the dual use build silent from a terminal. `cli/console.py` borrows the
console of whatever launched it, and does so **before the arguments are read**,
so that `--help` and argument errors land somewhere. Double-clicked there is no
console to borrow, and nothing is printed.

## The window

`ui/structura_gui.py` is the whole interface; `structura/__main__.py` is the
command line and one call into it. They share `settings.py` so neither has to
import the other.

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
- **Nothing is written over without being asked about, and the asking happens
  before the build runs.** `settle_collisions` compares `core.outputs` against
  the output folder and offers overwrite, a suggested free name, or stopping;
  a rename is checked again, because the name typed in may collide too. Doing
  this at the end would mean running a build nobody wanted.
- **A write that fails is a question, not a lost build.** The worker hands
  `core.set_retry` a callback that puts the question on the same queue every
  other message uses and waits on a queue of its own; `_drain_events` opens the
  dialog on the main thread. Nothing else is drained while it is up, which is
  what the build wants. A cancel sets `App.cancelled`, so the error the write
  then raises is reported as a choice rather than as a fault.
- **Big build mode borrows the offset fields and the name tags.** Their values
  are stashed and handed back when it is switched off, so flipping it twice
  leaves the window exactly as it was. Anything else that mode takes over has to
  do the same.
- **The window does not resize.** CustomTkinter draws every widget on a canvas
  of its own and repaints it whenever its size changes, about a millisecond
  each; with the widgets this window has, one step of a drag cost a quarter of a
  second. An empty window of the same kind manages six. It is a fixed
  `WINDOW_WIDE` by `WINDOW_TALL`, and everything inside it is a constant too --
  nothing measures a neighbour and applies the result, which used to settle in a
  visible flicker.
- **One scale, chosen once.** CustomTkinter otherwise makes the process
  per-monitor DPI aware and compensates in software: it fades a window to
  fifteen percent alpha and rebuilds every widget when it changes monitor.
  `_fix_scale()` declares the process aware of the *system* scale and hands
  CustomTkinter that number, so text stays sharp and nothing is ever rebuilt.
- **"Transparent" is not transparent.** A `CTkLabel` or `CTkEntry` with
  `fg_color="transparent"` fills its rectangle with the colour it finds behind
  it. A child as tall as its parent therefore paints over the parent's border.
  Keep children inset, and use `draw_every_pixel()` on anything with a rounded
  border -- the drawing code floors a widget's size to an even number first, and
  an odd one loses its last row.
- Screenshots in the README are generated by `tools/make_screenshots.py` from the
  running window. Change the interface, re-run it. It refuses to save unless the
  foreground window belongs to its own process, so leave the machine alone while
  it runs.
- **Settings live in `.structura`** -- next to the executable if one is there,
  which makes the program portable, and otherwise in the home directory, not
  beside the program, so they survive
  replacing the executable and work when it is run from a folder the user cannot
  write to. An older `settings.json` is read once to carry a choice over.
- **What is remembered describes the machine or the person, not the pack.** The
  theme, the language, the output folder, the TechPack mode and the low geometry
  switch are stored; the pack name, description, icon, offsets and transparency
  are not. Low geometry is stored because whether a client can afford detailed
  ghost blocks depends on the hardware and on Vibrant Visuals, and that answer
  does not change between structures. Every setter in `settings.py` writes the
  file, and `tests/test_interface.py` fails when a key in `DEFAULTS` has no
  setter it checks.
- **The program replaces itself, and the swap is a rename.** A running
  executable cannot be written over on Windows, but it can be moved: the running
  file is renamed to `Structura.exe.old`, the download is written where it
  stood, and the new build is started. Only a frozen build has anything to
  replace; from a checkout the About window says so.
- **Nothing is touched until the download has answered for itself.** It lands
  beside the running file as `Structura.exe.new`, and it has to arrive at the
  length the server declared, match the SHA-256 the release publishes for it in
  `SHA256SUMS.txt`, start with `MZ`, and then actually run:
  `updates.answers_for_itself` starts it with `--help` and requires it to exit
  zero. Both builds answer that, the windowed one included. This is what turns
  "the new build will not open" from something nobody is left alive to fix into
  a refusal with the old build still in place, and it is why there is no
  separate updater program. **A downloaded file must be probed by an absolute
  path** -- Windows searches for a bare name and appends `.exe` while it does,
  which never finds a file named `.new`.
- **A release with no fingerprints is refused, not taken on trust.**
  `updates.SUMS` and `build.SUMS_NAME` are the same file from its two ends, and
  a test fails when they drift. The format is `sha256sum`'s own, so the same
  asset checks a hand download. **This is not a signature.** The fingerprint
  travels with the build it describes, from the same release over the same
  connection, so it proves the file arrived whole, not that the release is the
  project's. Do not describe it as proving where a build came from.
- **A file operation in the update path is retried, not trusted.** Windows
  refuses to rename or replace a file another process has open, and an antivirus
  opens a freshly written executable to scan it. `updates.keep_trying` asks
  again for `updates.PATIENCE` seconds. If the second rename fails anyway the
  first is undone, so the folder is never left with nothing to run.
- **The displaced build is hidden, and the attribute travels.** `updates.hide`
  sets it only after the swap has succeeded, because a rollback renames that
  same file back into place and would hide the program itself. Clearing it
  races the process still shutting down, so `updates.clear_displaced()` is
  called with patience, on a thread of its own so the window never waits.
  Nothing depends on it winning: the leftover is what a broken update is
  recovered from, and any later launch clears it.
- **The first launch starts in the desktop's language.** With no language
  remembered, `system_locale.read()` asks the machine and `settings.match_locale`
  turns the answer into one of the files: that locale, then any file for the
  language, then English. It happens once, because the guess is written to the
  file like any other choice, so somebody who then picks English on a Spanish
  machine keeps English.

### The generated pack's name and description

`pack/manifest.py` owns both. The name shown in game is prefixed -- `Structura: <what
the user typed>` -- but **the UUID is still derived from the bare name**, because
folding the prefix in would have made every pack built by an older Structura look
like a different pack to the game and left players holding two copies.

The description is one field with newlines between its parts: the user's own note
first, then the name tags, then the TechPack version if bundled, then the credits
line. The credits colours are Minecraft formatting codes and each author keeps
the colour they have always had.

---

## Where the data lives

**The data lives inside the package.** `structura/lookups/`,
`structura/Vanilla_Resource_Pack/`, `structura/fonts/` and `structura/images/`
sit beside the code that opens them, and that is what makes the project
installable: setuptools ships package data only from under the package
directory, so a `pip install` of a project keeping them at the repository root
would install a program with no tables and no textures.

The release is also a **single self-contained executable**, and the same
directories — plus the shipped part of `be_tech_pack/` and `pyproject.toml` —
are packed inside it and unpacked at run time into the folder PyInstaller points
`sys._MEIPASS` at.

`be_tech_pack/` is a git submodule and seventy megabytes, so it cannot be package
data. A generated pack draws on about one megabyte of it, and **that megabyte is
staged into `structura/techpack/` and committed** by
`tools/stage_tech_pack.py` — which is what lets a pip install offer the TechPack
setting at all. The submodule stays the source of truth: **re-run the staging
script after updating it**, or a release ships the old assets.
`tests/test_tech_pack.py` fails when the two have drifted.

**Every data read goes through `paths.py`.** A hardcoded `open("lookups/...")`
works in a checkout with the right working directory and fails everywhere else,
which is the worst way for a bug to behave. `paths.data()` searches, in order:
beside the executable, inside the bundle, then the package itself.

Beside the executable wins on purpose: a bundle is read only, so anyone
hand-editing a lookup table to add a block can drop the folder next to the exe
and have it take effect without rebuilding.

`tests/test_paths.py` builds a pack with the working directory set to an empty
temporary folder. That is the cheap way to catch a module that still assumes the
checkout is the working directory -- a missing `import paths` shows up there as
the NameError it is, rather than only in a release nobody has run yet.

## Languages

**One file per language, in `lookups/lang/`.** `<locale>.lang`, one `key=value`
per line, UTF-8, `#` for a comment. Adding a language is adding a file and, if
its *language* has no colour yet, a line in `lookups/language_colors.json`.
Nothing lists the languages: `lang_parse.parse()` reads the folder.

**A language is named by its locale everywhere**, the way Minecraft names its
own: a language and a region, `en_US`, `es_MX`, `zh_CN`. The language part is
ISO 639-1 where there is one and ISO 639-2 where there is not, which is `ceb`
for Cebuano. The locale is the file's name, the key every table is read with,
the value the picker carries, and what `.structura` remembers, and **nothing
inside the file repeats it** -- a locale written in two places is one that can
disagree with itself.

**The language part is what a locale falls back to.** `ui_fonts` and
`lang_icons` ask for the locale and then for its language, so `zh_TW` is drawn
in the same face and the same colours as `zh_CN` without either being listed.
That is what makes adding Mexican Spanish beside Spain's a matter of adding a
file. `lang_parse.language_of` is the split.

**Two lines describe the language rather than label anything.** `language name`
is its own name for itself, which the picker shows and sorts by. `language
badge` is the letters on its badge, for the languages where the language part is
not the thing to show: `en_PT` reads PT, because Pirate Speak reading EN says
nothing. `lang_parse.META` names both, and the tests that compare one language
against another leave them out. Neither is the `language` line, which is the
word "language" translated, for the label beside the picker.

The picker leads with English, because it is the source the rest are translated
from, and then goes alphabetically by name. The special languages sit among the
real ones; nothing keeps them apart.

**The special languages are files too, and generated.**
`tools/make_special_languages.py` writes them from `en_US.lang` using the transforms
in `tools/lang_fun.py`, at the locales Minecraft itself uses: `en_PT` Pirate
Speak, `lol_US` LOLCAT, `en_WS` Shakespearean, `en_UD` upside-down English, and
`en_SGA` for Enchanting, which Minecraft has no language for because it is a
font. Sixty-odd strings times five is three hundred lines nobody would keep in
step. **Re-run it after changing an English string**; `tests/test_languages.py`
fails when they have drifted.

Two things to keep in mind when touching `tools/lang_fun.py`:

- **Format placeholders are protected.** The transforms run only over the text
  between `{}` markers. Reversing "Built {}" without that protection produces
  "}{ ..." and the next finished build raises on `.format()`.
- **Enchanting is an evocation, not the real alphabet.** Minecraft's enchanting
  table script is a *font* -- the glyphs are in the resource pack as
  `font/ascii_sga.png` and there is no Unicode block for them -- so no string of
  characters can be the genuine article. It is generated as English unchanged and
  drawn in the rune face `tools/make_fonts.py` builds from that sheet.

Badges are drawn by `ui/lang_icons.py`, coloured by
`lookups/language_colors.json`, which carries an entry for nearly every ISO code
and one per special language, so every entry in the picker is told apart by its
colours. **One badge is borrowed:** upside-down English wears the English badge
flipped top to bottom, letters and all, which turns the slant of the bands over
as well as the text. `lang_icons.UPSIDE_DOWN` is the only entry of its kind.

`docs/TRANSLATION.md` is what a translator reads; keep it in step with the files.

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

**`pyproject.toml`, `[project] version`.** That is where PEP 621 says a version
lives and where every packaging tool looks for it. **Bump it there and nowhere
else** — nothing in the tree hardcodes a version, and `structura.__version__`,
the window title, the release zip's name and the generated pack's manifest
version all come from it.

`version.py` reads it back, and has to do so three ways because Structura runs
three ways:

- **installed with pip** — `importlib.metadata`, the standard route
- **from a checkout** — there is no installed distribution, so `tomllib` parses
  the file
- **frozen** — there is no distribution metadata either, which is why both specs
  pack `pyproject.toml` into the bundle

`tomllib` is standard library from 3.11, which is what `requires-python` asks
for, so none of that costs a dependency. The answer is cached: it cannot change
while the program runs.

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

`Structura(pack_name)` makes a folder, then:

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

`structura.core` is the API any front end uses, and it is deliberately the only
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
| `get_lookup_version()` | which build of the tables produced it |
| `core.outputs(target, tags, block_lists, big)` | every file a build under that name would write |

Settings a caller can pass before generating: `set_opacity`, `set_description`,
`set_icon`, `set_model_offset`, `set_list_labels`, `set_low_geometry` and
`set_tech_pack`. Every one of them is in the fingerprint, so two packs that
differ by any of them are different packs. `set_retry` is the exception: it
describes what to do when a write fails rather than what the pack contains, so
it is not part of the fingerprint.

**`core.outputs` has to agree with what the build writes.** It is what a front
end asks before it starts, and it never looks again, so a file the build writes
without being named there is one that gets written over with nobody asked. Both
sides go through `pack_file` and `block_list_file`, and
`tests/test_overwrite.py` builds a real pack and compares the folder against
the list.

**A failed write is handed back, not thrown.** `set_retry` takes a callback
given the `OSError` and the path, and returning True runs the same write again.
Windows refuses to write a file another program holds open, and a pack the
player still has loaded is exactly that. With no callback the write raises,
which is what the command line wants: it refuses by name and points at
`--overwrite`.

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
`lookups/pack_icon.png` at 256×256 and `images/pack_icon.ico` from 16 px to 256 px —
by rendering the isometric S cube over `background_slimelab.png`. The grid
colour, its alpha and the S material are the constants at the top of that file.
Nothing is stored that the script cannot rebuild.

**No tool checks the icon rules.** This section used to claim the audit did;
it never has. If it matters, the check belongs in `tools/audit_blocks.py`.

### High and low geometry

Every ghost block is geometry the client lights and draws, and Vibrant Visuals
makes that markedly more expensive. A shape family may declare a simpler form of
itself under its own name plus `armor_stand_geo_class.LOW_SUFFIX` — `bell__low`
beside `bell` — and `simplify()` swaps to it when the pack is built with
`set_low_geometry(True)`. A family without one is drawn as it always is, which is
most of them.

`tools/make_low_geometry.py` generates those forms. **Re-run it after changing a
detailed shape**, or the simple form is still the old one's outline.

### The lookup tables

| File | What it holds |
| --- | --- |
| `lookups/block_definition.json` | block id → shape family. Missing entry means the block is skipped |
| `lookups/block_shapes.json` | shape family → cube sizes, offsets and the group pivot, per variant |
| `lookups/block_uv.json` | shape family → per-face UV sizes and offsets, per variant, plus texture overrides |
| `lookups/block_rotation.json` | shape family → rotation for each rotation state |
| `lookups/nbt_defs.json` | block state name → what it means (`rot`, `top`, `variant`, `data`, `shape`, `open_bit`, `hinge`) |
| `lookups/variants.json` | variant state value → index into a terrain_texture list |
| `lookups/material_list_names.json` | block id → the name shown in the block list |
| `lookups/lang/<locale>.lang` | UI strings, one file per language, named for its locale |

`block_shapes.json` and `block_uv.json` must agree. A variant that exists in one
and not the other silently falls back to `default`, which is how a snow layer
ends up wearing a full-height texture. Add variants to both.

**Not every state is in the states.** A copper golem statue keeps its pose in
the block entity beside the block, the way a sign keeps its text, so four statues
in four poses share one palette entry. `structure_reader.get_block_entity` reads
`block_position_data` and `structura.core.ENTITY_SHAPES` names the fields worth
reading — a block entity carries a great deal that has nothing to do with how a
block looks.

**A block drawn with an entity's model takes the model, not a box measured off a
picture.** `make_block_forms.unwrap` is the way Bedrock lays a box out on a
sheet and `make_block_forms.spun` is the turn a bone or a cube carries; the mob
heads and the copper golem statue both go through them. The statue's four poses
are four geometry files in the community submodule — `copper_golem`,
`copper_golem_sitting`, `copper_golem_running`, `copper_golem_star` — not one
shape leaned four ways.

**A block entity may hold another whole block, and then one position draws
two.** A flower pot keeps what is planted in it as `PlantBlock`, a compound with
a name and states of its own; `core.ENTITY_HOLDS` names that field and
`core.Structura._drawn_at` returns the pot and the plant. The plant is then
drawn by its own family with its own textures, which is why every pottable plant
works without a variant apiece.

**A rotation table needs every form of the value.** Bedrock gives some blocks a
numeric `direction` and others a `minecraft:cardinal_direction` string, and a
table with no entry for the value a block carries draws it unrotated, silently.
That is what made every door face the same way. The numbering is not the same for
every block either — see `docs/Block Notes.md`.

**A form may number its rotations differently from its family.** A
`"<variant>:<value>"` key in `block_rotation.json` is read before the plain
value. A hanging sign carries two rotation states and only one applies: fixed to
the block above it turns with `ground_sign_direction` in sixteen steps, and
swinging or wall mounted it turns with `facing_direction` in four, so 2 means
something different in each. `core._process_block` picks the state.

**A family turns about the middle of its block.** `center` in
`block_shapes.json` is that pivot. A family whose cubes all sit at one edge is
tempting to pivot on that edge instead, and that takes the block out of its own
block: a door pivoted on the plane of its own panel ended up half in the block
beside it a quarter turn round.

**One texture per cube, not per block.** A block built from several cubes cannot
use Bedrock's six face textures directly; every cube would get the same six. The
`overwrite` entry in `block_uv.json` gives a texture per cube per face, and a
value written `@up` or `@down` means "whatever this block declares for that
face", which is how one entry serves every wood a sign comes in.

**A small picture in a full sized file is the same trap.** `bell_side` is a
16×16 file with the bell drawn in an 8×9 corner of it, so a face working its own
window out from where its cube sits reads empty space and the bell is a flat
plate. Both pieces of the bell name their rows. `heavy_core.png` is the version
of that with three 8×8 pictures in one 16×16 file — top, bottom, side — and a
quarter of it empty. Every one of a dried ghast's twenty four textures is a
10×10 picture in a 16×16 file, four to a face, one per `rehydration_level`.

**A sheet in `textures/blocks/` still looks like a tile.**
`decorated_pot_base.png` is 32×32 and holds the neck's unwrap over the body's
top and bottom; `flower_pot.png` holds the rim over the wall. Faces left to work
their window out from where their cube sits read those as one picture, which is
how a decorated pot ends up with holes through it.
`make_block_forms.on_sheet` turns a region of a sheet into a texture reference
and a window, pulling the tile corner back far enough that the region fits and
never past the edge of the sheet.

**Only the top left 16×16 of a texture becomes a tile.** A larger one is cropped,
never scaled, so its pixels keep their size. **So a tile saved at the wrong scale
is a hole in the model, not a blurry block.** `fern` and `short_grass` were both
saved as ten times upscales, 160×160, and the corner Structura reads was empty,
so both drew nothing and neither reached the skipped list.
`tests/test_block_coverage.TileTests` fails on a supported block whose tile has
no pixels in it. A block drawn from an entity sized
sheet says which part it needs by writing `#x,y` after the texture's name, and
the window travels with an `@` reference: `"@north#0,12"` is the board half of
whatever sheet that wood has. Each window is a tile of its own, and one that
falls outside the texture is ignored.

**How a block is mounted is a different shape, not the same shape moved.**
`tools/make_block_forms.py` owns `hanging_sign`, `bell`, `grindstone`, `campfire`,
`shelf`, `tripwire_hook`, `sculk_shrieker`, `tripwire`, `flower_pot`,
`decorated_pot`, `brewing_stand`, `heavy_core`, `dried_ghast` and `door` in
both
tables, and gives each mounting its own list
of cubes. It also
gives a lit campfire its fire, which is the only thing telling it from a dead one
and a soul campfire from an ordinary one, gives a shelf a different picture
on each face, since its sheet holds four, and gives a tripwire hook the two
arrangements `attached_bit` names.

**A ghost block is not a solid one, so vanilla's own trick is not always the
answer.** Vanilla paints a shelf's three compartments into its front texture and
leaves the block a plain box, which reads correctly when the block is opaque and
reads as nothing at all when it is half transparent. The compartments are cut as
geometry here instead. The same reasoning gives a sculk shrieker its throat, and
`tools/make_string_texture.py` draws string a tile of its own because vanilla's
is a scatter of single faint pixels that disappears on a see-through plate.

**`blocks.json` names texture slots, not faces.** For most blocks the two are the
same, but `big_dripleaf` reads `up: big_dripleaf_side2`, `down:
big_dripleaf_side1` and the leaf on three of the sides, because the engine picks
from those slots for a model of its own. Taken literally, the leaf's top wears
four rows of edge profile over an empty tile and the block is invisible from
above. A family whose slots do not line up with its faces names its textures
outright in `overwrite`.

**The UV lists run in the shape list's order, cube for cube.** A family whose
entry was written beside another family's has to have its lists reordered to
match its own cubes, not only its numbers changed. `lightning_rod` was copied
from `end_rod`, whose two cubes are the same two the other way round, so the
base wore the rod's long stripe and the base's square was stretched along the
rod. Nothing reports this: both lists were the right length.

**A wall mounting sits at z 0.** `wall_sign` is the family to copy: its board is
at `z` 0 to 2, so the wall is the block behind it and the face looks along +z,
which is where the rotation tables put south. A bell's beam, a grindstone's legs,
a hanging sign's arm and a shelf's whole body all run that way.

**Edit the tables a family at a time.** `tools/lookup_writer.py` replaces one
family's span and leaves the rest of the file byte for byte alone. `block_uv.json`
is not formatted consistently, so rewriting it from a parsed copy reformats
entries nobody touched and buries the real change.

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

`pack/manifest.py` is the only thing that writes a generated pack's manifest.

- `format_version` is `2`, exactly one `resources` module, no scripts.
- **UUIDs are derived, not random.** `uuid5` over a fixed Structura namespace
  plus the pack name, so regenerating a pack replaces the one already in the
  player's list instead of appearing as an unrelated pack. Never go back to
  `uuid4` here; the accepted cost is that two people who pick the same pack name
  get the same UUID.
- The pack version is the Structura version, from `pyproject.toml`.

### Bundling TechPack

`pack/tech_pack.py` has three answers rather than two — `tech_pack.NONE`,
`COMPATIBILITY` and `FULL`, chosen with `set_tech_pack(mode)`, the **TechPack**
menu, or `--tech_pack none|compatibility|full`. The default is none: bundling
somebody else's pack into yours is a deliberate act, not something that happens
because a switch was left on, and the choice is remembered in `.structura`.

**Compatibility** merges TechPack's declarations onto the armor stand and ships
none of its files, so a separately installed TechPack keeps working alongside
the generated pack. **Full** copies its assets in as well, so the one pack is
both. `mode_of()` still reads a bare `True` as full, because the setting used to
be a switch and a stored one has to keep meaning what it did.

This exists because the two projects collide head on. Both replace
`entity/armor_stand.entity.json`, a client entity file replaces the vanilla one
rather than merging with it, and **between two packs only the higher in the
player's list is read at all**. Applying Structura and TechPack side by side
does not half-work: whichever sits lower is ignored completely. There is no
ordering that runs both, which is why bundling is the only answer and why the
README says to disable the standalone TechPack while a bundled pack is active.

The merge lives on `armorstand.merge_description`, not in `pack/tech_pack.py`, because
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

`pack/armor_stand_class.py` carries a hardcoded copy of vanilla's
`armor_stand.entity.json` description with this project's geometry and textures
added. A client entity file in a resource pack **replaces** the vanilla one;
they do not merge. Vanilla's own animation and render controllers keep asking
for the short names vanilla's copy declared, so every name the copy fails to
carry over is a `can't find animation <name>` in the content log and a vanilla
animation that stops playing.

This drifts on its own: Mojang adds a short name in an update and the hardcoded
copy, which never changed, is suddenly missing it. When a Minecraft update
lands, diff the `animations`, `scripts.animate` and `render_controllers` lists in
`pack/armor_stand_class.py` against
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
`docs/PROJECT_REVIEW.md`.

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
python tools/make_fonts.py                             rebuild the bundled faces
python tools/make_low_geometry.py                      the simplified shapes
python tools/make_bookshelf.py                         the bookshelf's 64 states
python tools/make_statue_poses.py                      the copper golem's four models
python tools/make_special_languages.py                    the five generated languages
python tools/make_block_forms.py                       the mounted forms, the fire and the shelf
python tools/make_growth_forms.py                      crops, eggs, compost, coral
python tools/make_furniture_forms.py                   beds, lecterns, conduits
python tools/make_head_forms.py                        the mob heads
python tools/make_container_forms.py                   shulker boxes and banners
python tools/make_banner_textures.py                   the sixteen dyed banners
python tools/make_string_texture.py                    the string tile a ghost can be seen with
```

`lookups/` and `Vanilla_Resource_Pack/` are opened by relative path, so all of
these must run from the repository root.

---

## Reference

- Bedrock samples: https://github.com/Mojang/bedrock-samples
- Community documentation: https://wiki.bedrock.dev/
- Vanilla listings:
  https://learn.microsoft.com/en-us/minecraft/creator/reference/content/vanillalistingsreference/?view=minecraft-bedrock-stable

# Writing Prose

Explore widely, output narrowly, keep conclusions simple.

You write brief, declarative prose, without personal pronouns, unsolicited additions, or em dashes.

You should prioritize perspicuity. The answer goes in the final sentence.

# Messages to Me

I am scanning your messages while doing something else. Long messages get skimmed, and the line that needed an answer gets missed. You are writing a status note, not marketing copy.

Put the result in the first line.

Keep only what I will act on. Cut the request I already made, the steps I watched you take, and any summary that repeats the first line.

Be precise. Use the real file name, the real value, the real error text.

Put questions last, each on its own line.

Always keep risks, mistakes, and guesses you made. Those stay in even when everything else goes.

Use plain sentences. One idea each. State the fact and stop.

Do not write for effect. If a sentence sounds quotable, rewrite it as a plain statement. Avoid:

- "load-bearing", "worth stating plainly", "worth naming", "worth flagging", "full stop", "carries the argument", "the trap is", "the real question is", "the honest answer is", "to be clear", "let me be direct"

- "real" or "actual" used for emphasis, like "a real tension" or "the actual problem"

- Any sentence that announces a point instead of making it. If a line can be deleted without losing information, delete it.

- "This is not X, it is Y" and "it isn't just X, it's Y"

- Sentence fragments used for emphasis, like "Not a bug. A design choice."

- Em dashes. Colons and semicolons used as a dramatic pause. Write "and", "but", or "because", or start a new sentence.

- Opening with agreement or praise, like "You're absolutely right" or "Great catch".

- Grading your own work: "successfully", "perfect", "now works flawlessly", "production ready".

Say what changed and what it means, in the words a coworker would use out loud. A good update reads like this:

> auth.ts: token refresh now runs only within 5 minutes of expiry. It used to run on every request. I also added logging for the 401s that were being dropped silently.

> Do you want the refresh window at 60 seconds instead of 5 minutes?

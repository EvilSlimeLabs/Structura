# Structura

![EvilSlimeLabs](structura/images/evilslimelabs-logo3.png)

**Maintained by [EvilSlimeLabs](https://github.com/EvilSlimeLabs).** Originally
created by DrAv0011, FondUnicycle and RavinMaddHatter, whose work this is built
on and who are credited in every pack it produces.

Structura turns a `.mcstructure` file into a Minecraft Bedrock resource pack.
The pack replaces the armor stand so it renders when off screen and carries
every block of your build as a bone in its model, drawn as semi-transparent
*ghost blocks* that show you exactly where the real blocks go. Inspired by
Litematica, and it needs no behaviour pack, no commands and no cheats — just a
resource pack and an armor stand, so it works in a survival, achievements-on
world.

[![Intro to Structura video](https://img.youtube.com/vi/IdKT925LKMM/0.jpg)](https://www.youtube.com/watch?v=IdKT925LKMM)

*(The video shows an older version. The program it demonstrates now looks like
the screenshots below, but the idea and the in-game result are the same.)*

---

## Breaking changes from 1.7

Structura is distributed as **single-file executables** now — one for each
platform, for the window and for the command line. You are not expected to
install Python or run any of the source directly, and everything below follows
from that.

| Was | Is now |
| --- | --- |
| `python structura.py` | `Structura.exe` — double-click for the window, or give it arguments in a terminal and it builds there instead |
| `python structura_cli.py` | `Structura-cli.exe`, the same command line with the window left out of the build; from a checkout, `python -m structura.cli` |
| `sh start.sh` on Linux | the Linux executable; the script is gone |
| **Bundle TechPack** on/off | a **TechPack** menu with three settings — see [TechPack](#techpack). The default is now **None**; a pack that used to be built with the toggle on wants **Full Pack** |
| Basic and Advanced screens | one screen |

**Packs built by 3.0 replace packs built by 1.7 only if the build is identical.**
A pack's identity is now derived from its contents — the structures, the
transparency, the icon, the description and every setting — rather than from its
name alone. Rebuilding an unchanged pack replaces the copy already in your list,
as before; changing anything about it produces a pack the game treats as a
different one, so both can sit in your list at once. Turning **Low Geometry** on
counts as a change.

For anyone working on the source rather than using it: everything importable is
now one `structura` package, so `from structura import Structura` replaces
`structura_core.structura`, and the entry points are `python -m structura` for
the window and `python -m structura.cli` for the command line.

---

## 1. Export a structure from Minecraft

Get a structure block — in a creative world with cheats on, run
`/give @s structure_block`.

![Giving yourself a structure block](docs/give_structure.png)

Set the structure block over your build and select every block you want in the
ghost model. A single structure block covers at most **64×64×64** without
editing your world's NBT data.

![Configuring the structure block](docs/select_structure.PNG)

Press **Export** at the bottom to save it to a file. Note where it goes; you
need it in a moment.

![Exporting the structure](docs/export_structure.PNG)

![The exported structure file](docs/exported.PNG)

---

## 2. Build the pack

Download `Structura.exe` and run it. That is the whole install — it is a single
self-contained file with everything inside it, so there is no folder to keep
together and nothing to extract. (A zip of the same executable is published
alongside it, for browsers and chat clients that refuse a bare `.exe`.)

![The Structura window](docs/window_dark.png)

Drop your `.mcstructure` file onto the window, or click the add area to browse
for it. Give the pack a name, and press **Make Pack**.

Each structure sits on its own row. Click the file name to swap in a different
file without losing the row, or the ✕ to drop it.

That is the whole flow. Everything else is optional:

| Setting | What it does |
| --- | --- |
| **Pack icon** | Click the preview to choose your own image. A small ✕ on it returns to the Structura icon. |
| **Short description** | Up to 25 characters, shown in the pack list in game. |
| **Block Transparency** | How see-through the ghost blocks are. 0 is solid, higher is fainter. Defaults to 65. |
| **Offset** | Moves the ghost model relative to the armor stand, per structure. |
| **Big Build Mode** | For builds larger than one structure block; see below. |
| **Make Block Lists** | Writes a text file of every block the build needs, beside the pack. |
| **Low Geometry** | Draws the most detailed blocks as simpler shapes; see below. |
| **TechPack** | What to do about the Bedrock Technical Resource Pack — see below. |
| **Output folder** | Where finished packs land. Defaults to `Structura Builds` in your Documents, and is remembered. |

**Name tags.** With a single structure the name tag is optional. Add a second
and it becomes required, because the tag is how you tell the armor stands apart:
name an armor stand `north wing` and it shows that structure. The window says so
as you type.

![Name tags become required with more than one structure](docs/window_validation.png)

**Big Build Mode** is for builds too large for one structure block. Export the
build in pieces, add them all, and Structura assembles them into one model
spread across the armor stand's layers.

The name tag fields step aside while it is on — big build mode names its own
models — and the offset becomes the **Corner** of the whole assembly. **Get
Global Cords** fills that in for you: every `.mcstructure` records where in the
world it was taken from, so the corner is the lowest of those origins, and the
ghost model lands back where the pieces came from without you reading
coordinates off the structure blocks.

Turning it off gives you your name tags and per-structure offsets back exactly
as they were.

![Big build mode](docs/window_big_build.png)

When the pack is written you get told, with the path and anything that had to be
skipped:

![The pack built dialog](docs/pack_built.png)

**Theme and language** sit in the bottom right, alongside a **?** that opens the
issue tracker and an **i** that says who made this. The theme follows your
desktop by default; light and dark are there if you would rather pin it.

![The window in light mode](docs/window_light.png)

Your theme, language and output folder are remembered in a `.structura` file.
Structura looks for one **next to the executable** first — put it there and the
program is portable, carrying its settings on a stick and touching nothing on
the host — and otherwise uses (and creates) one in your home directory.

### Languages

Labelled by ISO code rather than a flag, because a flag is a country and a
country is not a language.

**Real:** English, Українська, Español, 简体中文, Tagalog, Cebuano.

**Not real,** and badged in their own colours so you can tell:

| | |
| --- | --- |
| **Enchanting** | rune-like script, in the spirit of the enchanting table |
| **Pirate Speak** | *Hoist or drop an .mcstructure scroll t' include in this haul* |
| **LOLCAT** | *Gimme or drop an .mcstructure fiel to include in this pak* |
| **Shakespearean** | *Prithee add or drop an .mcstructure scroll* |
| **ɥsᴉlƃuƎ** | the whole window, upside down |

![Pirate Speak](docs/window_pirate.png)

The joke languages are generated from the English strings rather than stored, so
they cover every label automatically — including any added later.

![About](docs/about.png)

---

## 3. Use the pack in game

Apply the `.mcpack` like any resource pack — enabling it in your **global
resources** works well.

![Making the pack active](docs/make_pack_active.PNG)

Your structure now appears around **every armor stand** in the worlds you load.
That is how it works without a behaviour pack. Place an armor stand where the
build should go.

![Ghost blocks around an armor stand](docs/example_full.png)

**Shift-right-click** the armor stand to step through the build a layer at a
time. Layers 12 blocks apart share a step, so a tall build shows more than one
layer at once.

![One layer at a time](docs/example_layer.png)

---

## Low Geometry

Every ghost block is real geometry, and the game lights and draws each one.
Vibrant Visuals makes that markedly more expensive, so a large build of detailed
blocks can be demanding to render.

**Low Geometry** redraws only the blocks that carry the most detail — bells,
beacons, hanging signs, copper golem statues and the like — as simpler shapes.
They keep their textures and their positions, so the build still reads correctly;
they are just cheaper to display. Blocks that are already a cube or two are
untouched, which is most of them.

On a structure made entirely of detailed blocks it removes about two cubes in
five. On an ordinary build it changes almost nothing, because there is almost
nothing to simplify.

A pack built this way is a different pack from the same build at full detail, so
the two do not overwrite each other in your list.

Pass `--low_geometry` on the command line for the same thing.

---

## TechPack

Structura can work with the [Bedrock Technical Resource Pack](https://github.com/EvilSlimeLabs/Bedrock-Technical-Resource-Pack)
in one of three ways, chosen from the **TechPack** menu or with `--tech_pack` on
the command line.

**Why this needs a setting at all.** Both Structura and TechPack replace the
game's armor stand entity, and a resource pack *replaces* that file rather than
merging with it — between two packs, only the one higher in your list is read at
all. Applying them side by side does not half-work: whichever sits lower is
ignored completely, so you either lose the ghost blocks or you lose every
TechPack visualisation, depending on the order. No ordering gives you both.

| Choice | What you get |
| --- | --- |
| **None** | Structura alone. This is the default. |
| **Compatibility** | The generated pack declares TechPack on the armor stand but ships none of its files, so **your own** installed copy of TechPack keeps working alongside it. Keep both packs applied. |
| **Full Pack** | The generated pack carries TechPack's declarations *and* its assets, so this one pack is both. Apply only the generated pack, and remove or disable the standalone TechPack while it is active. |

Compatibility is the one to reach for if you already keep TechPack up to date
yourself. Full Pack is the one to reach for if you would rather hand somebody a
single file.

The bundled copy is whatever version of TechPack shipped with your Structura
build; it does not update on its own. For a newer TechPack, take a newer
Structura release or update the `be_tech_pack` submodule and rebuild.

---

## Command line

**`Structura.exe` is both programs.** Double-click it and the window opens; give
it arguments in a terminal and it builds a pack there instead and prints where it
landed.

```bash
Structura.exe --structure path/to/build.mcstructure --pack_name "CLI Pack" --overwrite
```

`Structura-cli.exe` is the same command line with the window left out of the
build — a smaller download for scripts, servers and batch jobs. It takes exactly
the same arguments; the only difference is that running it with nothing to build
tells you so instead of opening a window.

`--opacity` (1–100, the inverse of the window's transparency slider),
`--description`, `--icon`, `--output`, `--offset x,y,z`, `--low_geometry`,
`--tech_pack none|compatibility|full` and `--overwrite` are all available.
`--help` lists them. Without `--output` the pack lands in the same folder the
window uses.

### Installing it instead

You do not need to — the executables are the supported way to run Structura, and
they need nothing installed. But on any platform with **Python 3.11 or newer** it
can be installed as a package, which is the easier route for scripting and for
anything that wants to `import structura`:

```bash
pip install structura              # the library and the command line
pip install "structura[gui]"       # and the window
```

That puts two commands on your PATH, the same two the executables are:

```bash
structura --structure build.mcstructure --pack_name "My Pack"   # or no arguments for the window
structura-cli --structure build.mcstructure --pack_name "My Pack"
```

Everything travels with it — the lookup tables, the vanilla textures, the fonts
and TechPack's assets — so `--tech_pack full` works from an install exactly as it
does from the executable.

Two things the executables give you that an install does not. **Tkinter is not on
PyPI**: it ships with CPython on Windows and macOS, but on Linux it is a system
package (`python3-tk` on Debian and Ubuntu, `python3-tkinter` on Fedora), so the
`[gui]` extra needs that installed first. And `structura` here is a console
script rather than a windowed one, so on Windows it briefly shows a console.

From a checkout, `python -m structura` and `python -m structura.cli` are the same
two programs without installing anything.

## Linux

Download the Linux executable and run it; there is nothing to install.

The theme setting has one limitation here: CustomTkinter cannot read a Linux
desktop's light or dark preference, so **System** resolves to light. Pick
**Light** or **Dark** explicitly if that is not what you want.

Running from a checkout instead, you need the Tk package for your Python, which
does not come from PyPI:

```bash
sudo apt-get install python3-tk     # Debian/Ubuntu
sudo dnf install python3-tkinter    # Fedora
python3 -m pip install -r requirements.txt
python3 structura.py
```

## Building a release

Releases are built locally. The version comes from `[project] version` in
`pyproject.toml` — bump that first, then:

```bash
python -m pip install -e ".[dev]"
python build.py
```

`build.py` runs the unit tests, then freezes both entry points with PyInstaller:
`structura/__main__.py` through `structura.spec` into `Structura.exe`, and
`structura/cli/__main__.py` through `structura_cli.spec` into `Structura-cli.exe`, which
excludes the interface outright and comes out several megabytes smaller. Both go
into `dist/` along with `Structura-<version>.zip`. It prints the size and SHA-256
when it is done. The tests are not optional in the normal
path; `--skip-tests` and `--skip-freeze` exist for iterating on the packaging
step.

Everything the program reads — the lookup tables, the trimmed vanilla pack, the
TechPack assets, `pyproject.toml` and the branding — is packed **inside** the
executable. A copy of any of those folders placed *beside* the executable still
wins, which lets you override a lookup table by dropping an edited folder next
to the exe.

### Keeping the screenshots current

The window screenshots in this file are taken from the running program:

```bash
python tools/make_screenshots.py
```

Run it after any interface change and the documentation comes back in step. The
in-game screenshots are the ones only a person in a world can take.

## Updating blocks

You can add block support yourself and contribute it back.
[Here is a write-up on how that works](docs/Editing%20Blocks.md).

Two tools report where the coverage stands:

```bash
python tools/audit_blocks.py      # blocks whose textures do not resolve
python tools/coverage_report.py   # what the bundled test structures still drop
```

## Contributing

Contributions are welcome — see the [Contribution Guidelines](docs/CONTRIBUTING.md).

## Coverage

Every block in all 108 bundled test structures builds, and every block the
community vanilla resource pack defines has a Structura definition.
`docs/Block Notes.md` records what was decided and which shapes are still
approximations. Re-check at any time with `python tools/coverage_report.py`.

## Credits

- **EvilSlimeLabs** — current maintainer
- **DrAv0011**, **FondUnicycle**, **RavinMaddHatter** — original authors

Every generated pack carries these credits in its description.

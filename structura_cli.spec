# -*- mode: python ; coding: utf-8 -*-
# Driven by build.py, which runs the tests, freezes with this spec and then zips
# the executable. structura_cli.spec beside it builds the windowless twin from
# the same data, with the interface libraries excluded.
#
# The release is a **single self-contained executable**. Everything the
# program reads -- the lookup tables, the trimmed vanilla resource pack, the
# parts of the TechPack submodule a generated pack needs, the VERSION file and
# the branding -- is packed inside it and unpacked at run time into the private
# folder PyInstaller points sys._MEIPASS at. paths.py resolves every data read
# through there.
#
# A copy of any of those directories placed *beside* the executable still wins,
# which is what keeps the updater working: a bundle is read only, so an update
# drop lands next to the exe and paths.py finds it first.
#
# Also listed here is library data the program never names itself and so cannot
# find by path: CustomTkinter loads its colour themes and widget fonts from JSON
# inside its own package, and tkinterdnd2 loads a compiled tkdnd library.

import os

from PyInstaller.utils.hooks import collect_data_files

# --- Structura's own data --------------------------------------------------

## Source art and helper scripts that live in the data directories but have no
## business in a release. Kept in step with build.py.
SKIP_SUFFIXES = (".afphoto", ".xcf", ".psd", ".py", ".pyc")
SKIP_NAMES = {"easyItems.txt", "Thumbs.db", ".DS_Store"}

## be_tech_pack is a whole add-on repository; only the folders a generated pack
## actually draws from are worth carrying.
TECH_PACK_KEEP = ("animation_controllers", "animations", "entity", "materials",
                  "models", "particles", "render_controllers", "textures")


def tree(folder, into=None):
    """Every shippable file under `folder`, as PyInstaller (source, dest) pairs."""
    found = []
    into = into or folder
    for base, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            if name in SKIP_NAMES or name.lower().endswith(SKIP_SUFFIXES):
                continue
            source = os.path.join(base, name)
            target = os.path.join(into, os.path.relpath(base, folder))
            found.append((source, target))
    return found


datas = tree("lookups") + tree("Vanilla_Resource_Pack")
datas += [("VERSION", ".")]
## no window, so no fonts
for folder in TECH_PACK_KEEP:
    source = os.path.join("be_tech_pack", folder)
    if os.path.isdir(source):
        datas += tree(source, os.path.join("be_tech_pack", folder))
for extra in ("manifest.json", "LICENSE", "README.md"):
    path = os.path.join("be_tech_pack", extra)
    if os.path.isfile(path):
        datas += [(path, "be_tech_pack")]

# --- library data ----------------------------------------------------------

## The command line build has no window, so none of the interface libraries
## nor the fonts they draw with are carried.
hiddenimports = []




a = Analysis(
    ['structura_cli.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['customtkinter', 'tkinterdnd2', 'darkdetect',
              'structura_gui', 'ui_fonts', 'ui_icons', 'lang_icons'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Structura-cli',
    icon='pack_icon.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
